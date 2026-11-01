"""Preview and dry-run display formatting for CleanDownloads."""

from __future__ import annotations

from cleandownloads.scanner import ScanResult


def format_file_size(size_bytes: int) -> str:
    """Format bytes into human readable format (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_preview(scan_result: ScanResult, max_display: int | None = None) -> str:
    """Format dry-run preview matching exact product specifications."""
    ready_count = scan_result.total_ready
    lines: list[str] = []

    lines.append(f"PREVIEW — {ready_count} file{'s' if ready_count != 1 else ''} ready")
    lines.append("")

    if ready_count == 0:
        lines.append("  Downloads folder is already organized! No eligible files to move.")
        lines.append("")
        if scan_result.skipped_files:
            lines.append("SKIPPED FILES")
            lines.append("─" * 32)
            reasons: dict[str, int] = {}
            for sf in scan_result.skipped_files:
                reasons[sf.reason] = reasons.get(sf.reason, 0) + 1
            for reason, count in sorted(reasons.items()):
                lines.append(f"  {reason:<18} {count:>5}")
            lines.append("─" * 32)
            lines.append("")
        return "\n".join(lines)

    display_files = scan_result.ready_files
    if max_display and max_display < ready_count:
        display_files = scan_result.ready_files[:max_display]

    downloads_dir_name = scan_result.downloads_dir.name or "Downloads"

    for f in display_files:
        rel_source = f.path.name
        rel_dest = str(f.destination_relative_path).replace("\\", "/")
        size_str = format_file_size(f.size_bytes)

        lines.append(f"{f.filename}  ({size_str})")
        lines.append(f"  {downloads_dir_name}/{rel_source}")
        lines.append(f"  → {downloads_dir_name}/{rel_dest}")
        lines.append("")

    if max_display and max_display < ready_count:
        remaining = ready_count - max_display
        lines.append(f"  ... and {remaining} more files.")
        lines.append("")

    # Category breakdown table
    lines.append("FILE BREAKDOWN")
    lines.append("─" * 32)
    for category, count in sorted(scan_result.category_breakdown.items(), key=lambda x: -x[1]):
        lines.append(f"  {category:<18} {count:>5}")
    lines.append("─" * 32)
    lines.append(f"  {'Total':<18} {ready_count:>5} ({format_file_size(scan_result.total_ready_bytes)})")
    lines.append("")

    if scan_result.skipped_files:
        lines.append("SKIPPED FILES")
        lines.append("─" * 32)
        reasons = {}
        for sf in scan_result.skipped_files:
            reasons[sf.reason] = reasons.get(sf.reason, 0) + 1
        for reason, count in sorted(reasons.items()):
            lines.append(f"  {reason:<18} {count:>5}")
        lines.append("─" * 32)
        lines.append("")

    lines.append("No files have been moved yet.")
    return "\n".join(lines)
