import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from cleandownloads import __version__
from cleandownloads.config import ConfigManager
from cleandownloads.history import HistoryDB
from cleandownloads.organizer import Organizer
from cleandownloads.preview import format_file_size, format_preview
from cleandownloads.safety import OperationLockError, get_app_data_dir
from cleandownloads.scanner import Scanner
from cleandownloads.scheduler import WindowsScheduler
from cleandownloads.undo import UndoEngine

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Terminal formatting helpers
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner() -> None:
    """Print the CleanDownloads header."""
    banner = f"""{CYAN}{BOLD}
   CLEAN DOWNLOADS{RESET} {DIM}v{__version__}{RESET}
   {DIM}One command. Zero clutter.{RESET}
   ────────────────────────────────"""
    print(banner)


def cmd_interactive(config_mgr: ConfigManager, history_db: HistoryDB) -> None:
    """Display interactive main menu as specified in Section 5."""
    while True:
        # Safe screen clear via ANSI escape code (no subprocess / binary search)
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

        print_banner()

        scanner = Scanner(config_mgr.config)
        scan_res = scanner.scan()

        ready_count = scan_res.total_ready
        already_org = scan_res.already_organized_count
        total_scanned = scan_res.total_scanned

        print(f"\n   Downloads scanned: {BOLD}{total_scanned:<8}{RESET}")
        print(f"   Files ready:       {GREEN}{BOLD}{ready_count:<8}{RESET}")
        print(f"   Already organized: {DIM}{already_org:<8}{RESET}")

        print(f"\n   {BOLD}FILE BREAKDOWN{RESET}\n")
        breakdown = scan_res.category_breakdown
        if breakdown:
            for cat, count in sorted(breakdown.items(), key=lambda x: -x[1]):
                print(f"   {cat:<16} {count:>4}")
        else:
            print(f"   {DIM}No files waiting to be organized.{RESET}")

        print("\n   ────────────────────────────────\n")
        print("   [1] Preview changes")
        print("   [2] Organize Downloads")
        print("   [3] Undo last operation")
        print("   [4] View history")
        print("   [5] Settings")
        print("   [6] Exit")
        print()

        try:
            choice = input("   Select an option (1-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n")
            break

        if choice == "1":
            print("\n")
            print(format_preview(scan_res))
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "2":
            print("\n")
            if ready_count == 0:
                print(f"   {YELLOW}No files to organize.{RESET}")
            else:
                confirm = input(f"   Move {ready_count} files now? (Y/n): ").strip().lower()
                if confirm in ("", "y", "yes"):
                    organizer = Organizer(config_mgr.config, history_db=history_db, scanner=scanner)
                    print()
                    try:
                        res = organizer.organize(
                            scan_result=scan_res,
                            on_progress=lambda f, dest: print(f"   {GREEN}✔{RESET} {f.filename} → {dest.name}"),
                            on_error=lambda f, err: print(f"   {RED}✘{RESET} {f.filename}: {err}"),
                        )
                        print(f"\n   {GREEN}{BOLD}Organization complete!{RESET} Moved {res.successful_moves} files.")
                        if res.failed_moves > 0:
                            print(f"   {RED}Warning: {res.failed_moves} files could not be moved.{RESET}")
                    except OperationLockError:
                        print(f"\n   {RED}Another CleanDownloads organize or undo operation is currently running.{RESET}")
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "3":
            print("\n")
            undo_engine = UndoEngine(history_db)
            try:
                res_undo = undo_engine.undo_last()
                if not res_undo:
                    print(f"   {YELLOW}No recent organization operation available to undo.{RESET}")
                else:
                    print(f"   {GREEN}{BOLD}Undo finished:{RESET} Restored {res_undo.success_count} files.")
                    for rf in res_undo.restored_files:
                        print(f"   {GREEN}↩{RESET} Restored: {rf.original_path.name}")
                    if res_undo.fail_count > 0:
                        print(f"\n   {RED}Failed to restore {res_undo.fail_count} files:{RESET}")
                        for ff in res_undo.failed_files:
                            print(f"   {RED}✘{RESET} {ff.moved_from_path.name}: {ff.reason}")
            except OperationLockError:
                print(f"\n   {RED}Another CleanDownloads organize or undo operation is currently running.{RESET}")
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "4":
            print("\n")
            cmd_history(history_db, limit=10)
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice == "5":
            print("\n")
            cmd_config_menu(config_mgr)
            input(f"\n{DIM}Press Enter to return to menu...{RESET}")
        elif choice in ("6", "q", "exit"):
            print("\n   Goodbye!\n")
            break


def cmd_scan(config_mgr: ConfigManager, json_mode: bool = False) -> None:
    """Run scanner and display scan summary."""
    scanner = Scanner(config_mgr.config)
    res = scanner.scan()

    if json_mode:
        data = {
            "downloads_dir": str(res.downloads_dir),
            "total_ready": res.total_ready,
            "total_ready_bytes": res.total_ready_bytes,
            "already_organized_count": res.already_organized_count,
            "category_breakdown": res.category_breakdown,
            "ready_files": [
                {
                    "filename": f.filename,
                    "extension": f.extension,
                    "category": f.category,
                    "subfolder": f.classification.subfolder,
                    "size_bytes": f.size_bytes,
                    "source_path": str(f.path),
                    "target_relative_path": str(f.destination_relative_path).replace("\\", "/"),
                }
                for f in res.ready_files
            ],
            "skipped_files": [
                {"path": str(sf.path), "reason": sf.reason}
                for sf in res.skipped_files
            ],
        }
        print(json.dumps(data, indent=2))
        return

    print_banner()
    print(f"\nTarget Directory:  {res.downloads_dir}")
    print(f"Files Ready:       {GREEN}{BOLD}{res.total_ready}{RESET} ({format_file_size(res.total_ready_bytes)})")
    print(f"Already Organized: {DIM}{res.already_organized_count}{RESET}")
    print(f"Skipped / Ignored: {len(res.skipped_files)}")

    if res.ready_files:
        print("\nBreakdown by Category:")
        for cat, cnt in sorted(res.category_breakdown.items(), key=lambda x: -x[1]):
            print(f"  • {cat:<16} {cnt:>4} files")

    if res.skipped_files:
        print(f"\n{DIM}Skipped files summary:{RESET}")
        reasons: dict[str, int] = {}
        for sf in res.skipped_files:
            reasons[sf.reason] = reasons.get(sf.reason, 0) + 1
        for reason, count in reasons.items():
            print(f"  • {reason:<22} {count}")
    print()


def cmd_preview(config_mgr: ConfigManager, json_mode: bool = False) -> None:
    """Display dry-run preview."""
    scanner = Scanner(config_mgr.config)
    res = scanner.scan()
    if json_mode:
        organizer = Organizer(config_mgr.config, scanner=scanner)
        plan = organizer.plan(res)
        data = {
            "downloads_dir": str(plan.downloads_dir),
            "total_files": plan.total_files,
            "total_bytes": plan.total_bytes,
            "planned_moves": [
                {
                    "source": str(m.source),
                    "destination": str(m.destination),
                    "file_size": m.file_size,
                    "category": m.category,
                    "extension": m.extension,
                }
                for m in plan.planned_moves
            ],
            "skipped_files": [
                {"path": str(sf.path), "reason": sf.reason}
                for sf in res.skipped_files
            ],
        }
        print(json.dumps(data, indent=2))
        return

    print_banner()
    print()
    print(format_preview(res))


def cmd_organize(
    config_mgr: ConfigManager,
    history_db: HistoryDB,
    dry_run: bool = False,
    json_mode: bool = False,
    scheduled: bool = False,
) -> None:
    """Execute organization or dry run."""
    organizer = Organizer(config_mgr.config, history_db=history_db)

    try:
        if json_mode:
            res = organizer.organize(dry_run=dry_run)
            data = {
                "batch_id": res.batch_id,
                "total_files": res.total_files,
                "successful_moves": res.successful_moves,
                "failed_moves": res.failed_moves,
                "is_dry_run": res.is_dry_run,
                "moved_items": [
                    {
                        "source": str(m.source),
                        "destination": str(m.destination),
                        "file_size": m.file_size,
                        "category": m.category,
                        "operation_id": m.operation_id,
                    }
                    for m in res.moved_items
                ],
                "failed_items": [
                    {
                        "source": str(f.source),
                        "target_destination": str(f.target_destination),
                        "error": f.error,
                        "category": f.category,
                    }
                    for f in res.failed_items
                ],
            }
            print(json.dumps(data, indent=2))
            return

        if not scheduled:
            print_banner()
            if dry_run:
                print(f"\n{YELLOW}[DRY RUN MODE — No files will be moved]{RESET}\n")
            else:
                print("\nOrganizing Downloads folder...\n")

        res = organizer.organize(
            dry_run=dry_run,
            on_progress=lambda f, dest: print(f"  {GREEN}✔{RESET} {f.filename} → {dest}") if not scheduled else None,
            on_error=lambda f, err: print(f"  {RED}✘{RESET} {f.filename}: {err}") if not scheduled else None,
        )

        if not scheduled:
            if dry_run:
                print(f"\n{CYAN}Dry run complete.{RESET} {res.total_files} files ready to organize.")
            else:
                print(f"\n{GREEN}{BOLD}Organization complete!{RESET}")
                print(f"  Successful moves: {res.successful_moves}")
                if res.failed_moves > 0:
                    print(f"  {RED}Failed moves:     {res.failed_moves}{RESET}")
                if res.batch_id:
                    print(f"  {DIM}Operation Batch ID: {res.batch_id}{RESET}")
                    print(f"  {DIM}To reverse this operation, run: cleandownloads undo{RESET}")
            print()
    except OperationLockError:
        if scheduled:
            sys.exit(75)
        if json_mode:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "locked",
                        "message": "Another CleanDownloads organize or undo operation is currently running.",
                    },
                    indent=2,
                )
            )
            sys.exit(1)
        print(
            f"\n{RED}Error: Another CleanDownloads organize or undo operation is currently running.{RESET}\n",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_undo(
    history_db: HistoryDB,
    batch_id: str | None = None,
    json_mode: bool = False,
) -> None:
    """Execute undo operation."""
    undo_engine = UndoEngine(history_db)

    try:
        if batch_id:
            res = undo_engine.undo_batch(batch_id)
        else:
            res = undo_engine.undo_last()
    except OperationLockError:
        if json_mode:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": "locked",
                        "message": "Another CleanDownloads organize or undo operation is currently running.",
                    },
                    indent=2,
                )
            )
            sys.exit(1)
        print(
            f"\n{RED}Error: Another CleanDownloads organize or undo operation is currently running.{RESET}\n",
            file=sys.stderr,
        )
        sys.exit(1)

    if json_mode:
        if not res:
            print(json.dumps({"success": False, "message": "No operation available to undo"}, indent=2))
            return
        data = {
            "batch_id": res.batch_id,
            "total_attempted": res.total_attempted,
            "success_count": res.success_count,
            "fail_count": res.fail_count,
            "restored_files": [
                {
                    "operation_id": rf.operation_id,
                    "original_path": str(rf.original_path),
                    "moved_from_path": str(rf.moved_from_path),
                    "actual_restored_path": str(rf.actual_restored_path),
                }
                for rf in res.restored_files
            ],
            "failed_files": [
                {
                    "operation_id": ff.operation_id,
                    "moved_from_path": str(ff.moved_from_path),
                    "target_path": str(ff.target_path),
                    "reason": ff.reason,
                }
                for ff in res.failed_files
            ],
        }
        print(json.dumps(data, indent=2))
        return

    print_banner()
    if not res:
        print(f"  {YELLOW}No active operation batch available to undo.{RESET}\n")
        return

    print(f"  {GREEN}{BOLD}Restored:{RESET} {res.success_count} files")
    for rf in res.restored_files:
        print(f"  {GREEN}↩{RESET} {rf.original_path.name}")

    if res.fail_count > 0:
        print(f"\n  {RED}Failed to restore {res.fail_count} files:{RESET}")
        for ff in res.failed_files:
            print(f"  {RED}✘{RESET} {ff.moved_from_path.name}: {ff.reason}")
    print()


def cmd_history(
    history_db: HistoryDB, limit: int = 10, json_mode: bool = False
) -> None:
    """Show recent operation history."""
    batches = history_db.get_recent_batches(limit=limit)

    if json_mode:
        data = {
            "batches": [
                {
                    "id": b.id,
                    "timestamp": b.timestamp,
                    "total_files": b.total_files,
                    "successful_moves": b.successful_moves,
                    "failed_moves": b.failed_moves,
                    "status": b.status,
                    "notes": b.notes,
                }
                for b in batches
            ]
        }
        print(json.dumps(data, indent=2))
        return

    print_banner()
    print(f"\n{BOLD}RECENT OPERATION HISTORY{RESET}\n")
    if not batches:
        print(f"  {DIM}No operation history found.{RESET}\n")
        return

    print(f"  {'Batch ID':<36}  {'Timestamp':<20}  {'Moved':<6}  {'Status'}")
    print("  " + "─" * 74)
    for b in batches:
        ts_formatted = b.timestamp[:19].replace("T", " ")
        status_color = GREEN if b.status == "COMPLETED" else (YELLOW if b.status == "UNDONE" else RED)
        print(f"  {b.id:<36}  {ts_formatted:<20}  {b.successful_moves:<6}  {status_color}{b.status}{RESET}")
    print()


def cmd_status(
    config_mgr: ConfigManager, history_db: HistoryDB, json_mode: bool = False
) -> None:
    """Display status of CleanDownloads installation, paths, and scheduler."""
    cfg = config_mgr.config
    stats = history_db.get_overall_stats()
    scheduler = WindowsScheduler()
    sched_status = scheduler.get_status()

    if json_mode:
        data = {
            "version": __version__,
            "downloads_dir": str(cfg.get_resolved_downloads_dir()),
            "app_data_dir": str(get_app_data_dir()),
            "recursive": cfg.recursive,
            "rules_count": len(cfg.rules),
            "stats": stats,
            "scheduler": {
                "is_registered": sched_status.is_registered,
                "is_enabled": sched_status.is_enabled,
                "next_run_time": sched_status.next_run_time,
                "last_run_time": sched_status.last_run_time,
            },
        }
        print(json.dumps(data, indent=2))
        return

    print_banner()
    cfg = config_mgr.config
    stats = history_db.get_overall_stats()
    scheduler = WindowsScheduler()
    sched_status = scheduler.get_status()

    print(f"\n{BOLD}SYSTEM & CONFIGURATION STATUS{RESET}\n")
    print(f"  Version:               {__version__}")
    print(f"  Downloads Directory:   {cfg.get_resolved_downloads_dir()}")
    print(f"  App Data Directory:    {get_app_data_dir()}")
    print(f"  Recursive Scanning:    {cfg.recursive}")
    print(f"  Active Organized Files:{stats['active_organized_files']}")
    print(f"  Total Batches Run:     {stats['total_batches']}")
    print(f"  Total Undone Files:    {stats['total_undone_files']}")

    print(f"\n{BOLD}AUTOMATIC SCHEDULER STATUS{RESET}\n")
    if sched_status.is_registered:
        status_str = f"{GREEN}Enabled{RESET}" if sched_status.is_enabled else f"{YELLOW}Disabled{RESET}"
        print(f"  Status:                {status_str}")
        if sched_status.next_run_time:
            print(f"  Next Run Time:         {sched_status.next_run_time}")
        if sched_status.last_run_time:
            print(f"  Last Run Time:         {sched_status.last_run_time}")
    else:
        print(f"  Status:                {DIM}Not Configured (Run 'cleandownloads schedule --enable hourly' to enable){RESET}")
    print()


def cmd_config_menu(config_mgr: ConfigManager) -> None:
    """Display and manage settings."""
    cfg = config_mgr.config
    print(f"{BOLD}SETTINGS{RESET}")
    print("─" * 32)
    print(f"  Downloads Folder:  {cfg.get_resolved_downloads_dir()}")
    print(f"  Recursive Scan:    {cfg.recursive}")
    print(f"  Rules Configured:  {len(cfg.rules)}")
    print(f"  Ignored Exts:      {', '.join(cfg.ignored_extensions)}")
    print()
    print("  To edit rules directly, modify:")
    print(f"  {config_mgr.config_path}")


def cmd_schedule(args: argparse.Namespace) -> None:
    """Handle schedule subcommands."""
    scheduler = WindowsScheduler()
    if args.enable:
        success, msg = scheduler.register(args.enable)
        if success:
            print(f"{GREEN}✔{RESET} {msg}")
        else:
            print(f"{RED}✘{RESET} {msg}")
    elif args.disable:
        success, msg = scheduler.disable()
        print(f"{GREEN}✔{RESET} {msg}" if success else f"{RED}✘{RESET} {msg}")
    elif args.remove:
        success, msg = scheduler.delete()
        print(f"{GREEN}✔{RESET} {msg}" if success else f"{RED}✘{RESET} {msg}")
    else:
        status = scheduler.get_status()
        print(f"Scheduled Task: {'Registered' if status.is_registered else 'Not Registered'}")
        if status.is_registered:
            print(f"Enabled: {status.is_enabled}")
            if status.next_run_time:
                print(f"Next Run: {status.next_run_time}")


def cmd_uninstall() -> None:
    """Instructions and trigger for clean uninstallation."""
    print_banner()
    print(f"\n{YELLOW}{BOLD}UNINSTALL CLEANDOWNLOADS{RESET}\n")
    print("  To uninstall CleanDownloads cleanly:")
    print("  Run this command in PowerShell:\n")
    print(f"  {CYAN}& \"$env:LOCALAPPDATA\\CleanDownloads\\uninstall.ps1\"{RESET}\n")
    print("  This removes all launchers, scheduled tasks, and PATH entries without touching your files.")


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--json", action="store_true", default=argparse.SUPPRESS, help="Output machine-readable JSON"
    )
    common_parser.add_argument(
        "-d", "--downloads-dir", type=str, default=argparse.SUPPRESS, help="Override target Downloads directory"
    )
    common_parser.add_argument(
        "--min-age", type=int, default=argparse.SUPPRESS, help="Minimum file age in seconds before moving (default: 300)"
    )

    parser = argparse.ArgumentParser(
        prog="cleandownloads",
        description="One command. Zero clutter. Smart Downloads folder organizer for Windows.",
        parents=[common_parser],
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # scan
    subparsers.add_parser("scan", parents=[common_parser], help="Scan Downloads folder and display file analysis")

    # preview
    subparsers.add_parser("preview", parents=[common_parser], help="Preview planned file organization changes")

    # organize
    org_parser = subparsers.add_parser("organize", parents=[common_parser], help="Organize files in Downloads folder")
    org_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate organization without moving any files"
    )
    org_parser.add_argument(
        "--scheduled", action="store_true", help="Run in automated scheduled mode (exits quietly if locked)"
    )

    # undo
    undo_parser = subparsers.add_parser("undo", parents=[common_parser], help="Undo previous file organization operations")
    undo_parser.add_argument(
        "--batch-id", type=str, default=None, help="Specific batch ID to undo (defaults to latest)"
    )

    # history
    hist_parser = subparsers.add_parser("history", parents=[common_parser], help="Show past organization history")
    hist_parser.add_argument(
        "--limit", type=int, default=10, help="Number of recent batches to show (default: 10)"
    )

    # status
    subparsers.add_parser("status", parents=[common_parser], help="Show current application status and configuration")

    # config
    cfg_parser = subparsers.add_parser("config", parents=[common_parser], help="View or modify configuration")
    cfg_parser.add_argument("--reset", action="store_true", help="Reset configuration to defaults")
    cfg_parser.add_argument("--path", action="store_true", help="Show path to configuration file")

    # schedule
    sched_parser = subparsers.add_parser("schedule", parents=[common_parser], help="Manage automated background scheduling")
    sched_parser.add_argument(
        "--enable",
        choices=["30m", "hourly", "daily", "logon"],
        help="Enable automated task with specified frequency",
    )
    sched_parser.add_argument("--disable", action="store_true", help="Disable automated task")
    sched_parser.add_argument("--remove", action="store_true", help="Remove scheduled task")
    sched_parser.add_argument("--status", action="store_true", help="Show scheduled task status")

    # uninstall
    subparsers.add_parser("uninstall", parents=[common_parser], help="Show uninstallation guide or trigger uninstall")

    return parser


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    config_mgr = ConfigManager()
    if getattr(args, "downloads_dir", None):
        config_mgr.config.downloads_dir = str(Path(args.downloads_dir).resolve())
    if hasattr(args, "min_age"):
        config_mgr.config.min_file_age_seconds = max(0, args.min_age)
    history_db = HistoryDB()

    if not args.command:
        # Launch interactive menu if run without subcommands
        cmd_interactive(config_mgr, history_db)
        return

    json_mode = getattr(args, "json", False)

    if args.command == "scan":
        cmd_scan(config_mgr, json_mode=json_mode)
    elif args.command == "preview":
        cmd_preview(config_mgr, json_mode=json_mode)
    elif args.command == "organize":
        cmd_organize(
            config_mgr,
            history_db,
            dry_run=args.dry_run,
            json_mode=json_mode,
            scheduled=getattr(args, "scheduled", False),
        )
    elif args.command == "undo":
        cmd_undo(history_db, batch_id=args.batch_id, json_mode=json_mode)
    elif args.command == "history":
        cmd_history(history_db, limit=args.limit, json_mode=json_mode)
    elif args.command == "status":
        cmd_status(config_mgr, history_db, json_mode=json_mode)
    elif args.command == "config":
        if json_mode:
            print(json.dumps(asdict(config_mgr.config), indent=2))
        elif args.reset:
            config_mgr.reset_to_defaults()
            print(f"{GREEN}✔ Configuration reset to factory defaults.{RESET}")
        elif args.path:
            print(config_mgr.config_path)
        else:
            cmd_config_menu(config_mgr)
    elif args.command == "schedule":
        cmd_schedule(args)
    elif args.command == "uninstall":
        cmd_uninstall()


if __name__ == "__main__":
    main()
