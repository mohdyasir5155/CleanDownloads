# CleanDownloads — Usage Guide

## Interactive Terminal Manager

Running `cleandownloads` with no arguments launches the interactive console dashboard:

```powershell
cleandownloads
```

```text
   CLEAN DOWNLOADS v1.0.0
   One command. Zero clutter.
   ────────────────────────────────

   Downloads scanned: 248
   Files ready:       146
   Already organized: 102

   FILE BREAKDOWN

   Documents       38
   Images          42
   Videos          12
   Archives        19
   Software         8
   Code            11
   Others          16

   ────────────────────────────────

   [1] Preview changes
   [2] Organize Downloads
   [3] Undo last operation
   [4] View history
   [5] Settings
   [6] Exit
```

---

## Command-Line Subcommands

CleanDownloads can also be called directly with subcommands for scripts, CI/CD, or terminal power users:

| Command | Description |
|---|---|
| `cleandownloads scan` | Analyzes Downloads folder and prints category statistics without moving files |
| `cleandownloads preview` | Shows a before & after path preview of every file ready to be organized |
| `cleandownloads organize` | Moves all eligible files into organized category folders safely |
| `cleandownloads organize --dry-run` | Runs full simulation without moving any files |
| `cleandownloads undo` | Safely reverses the most recent organization run |
| `cleandownloads undo --batch-id <ID>` | Reverses a specific operation batch by ID |
| `cleandownloads history` | Lists recent organization runs and status from SQLite |
| `cleandownloads status` | Displays configuration, paths, active stats, and scheduler status |
| `cleandownloads schedule --enable hourly` | Configures automated background task via Windows Task Scheduler |
| `cleandownloads schedule --disable` | Pauses scheduled task |
| `cleandownloads schedule --remove` | Deletes scheduled task completely |
| `cleandownloads uninstall` | Guides clean removal of the application |

---

## Automatic Scheduling

Automated organization is disabled by default and requires explicit consent:

```powershell
# Run every 30 minutes
cleandownloads schedule --enable 30m

# Run every 1 hour
cleandownloads schedule --enable hourly

# Run daily at 09:00
cleandownloads schedule --enable daily

# Run on user login
cleandownloads schedule --enable logon

# Check scheduler status
cleandownloads schedule --status

# Disable or remove
cleandownloads schedule --disable
cleandownloads schedule --remove
```
