# Test Case B: First Application Launch & CLI Commands Testing
param(
    [string]$QaRoot = "C:\CleanDownloads-QA"
)

$ErrorActionPreference = "Stop"
$logFile = Join-Path $QaRoot "TestLogs\application-log.txt"
$testResults = @{
    TestId = "TC-B"
    Name = "First Application Launch & CLI Commands Verification"
    Passed = $true
    CommandsTested = @()
    Failures = @()
}

function Log-Step($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

Log-Step "Starting Test Case B: First Application Launch & CLI Commands Verification..."

try {
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { $localAppData = Join-Path $env:USERPROFILE "AppData\Local" }
    $installDir = Join-Path $localAppData "CleanDownloads"
    $venvPython = Join-Path $installDir "venv\Scripts\python.exe"
    $testDownloads = Join-Path $QaRoot "TestDownloads"
    $env:CLEANDOWNLOADS_DOWNLOADS_DIR = $testDownloads
    if (-not (Test-Path $testDownloads)) { New-Item -ItemType Directory -Path $testDownloads -Force | Out-Null }

    # Configure CleanDownloads to use isolated TestDownloads folder
    $configPath = Join-Path $installDir "config.json"
    $configContent = @{
        downloads_dir = $testDownloads
        default_fallback_folder = "Other"
        ignored_extensions = @("crdownload", "part", "tmp")
        excluded_directories = @("Documents", "Images", "Videos", "Audio", "Archives", "Software", "Code", "Other")
    }
    # Load default rules from app source if available
    $repoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
    $defaultRulesFile = Join-Path $repoRoot "config\default_rules.json"
    if (Test-Path $defaultRulesFile) {
        $rawConfig = Get-Content $defaultRulesFile -Raw | ConvertFrom-Json
        $configContent.rules = $rawConfig.rules
    }
    $configContent | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
    Log-Step "Configured CleanDownloads to point to isolated test directory: $testDownloads"

    # Populate sample files in TestDownloads
    $generatorScript = Join-Path $PSScriptRoot "generate_test_files.py"
    & $venvPython $generatorScript $testDownloads
    Log-Step "Generated fresh test dataset in $testDownloads"

    # List of commands to test
    $commands = @(
        @{ Cmd = "scan"; ExpectedExit = 0; Desc = "Scan command" },
        @{ Cmd = "preview"; ExpectedExit = 0; Desc = "Preview command" },
        @{ Cmd = "organize --dry-run"; ExpectedExit = 0; Desc = "Organize dry-run command" },
        @{ Cmd = "status"; ExpectedExit = 0; Desc = "Status command" },
        @{ Cmd = "history"; ExpectedExit = 0; Desc = "History command" },
        @{ Cmd = "config"; ExpectedExit = 0; Desc = "Config command" },
        @{ Cmd = "invalid_subcommand_test"; ExpectedExit = 2; Desc = "Invalid argument error handling" }
    )

    foreach ($item in $commands) {
        $cmdArgs = $item.Cmd.Split(" ")
        Log-Step "Testing: cleandownloads $($item.Cmd)..."
        
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = $venvPython
        $pinfo.Arguments = "-m cleandownloads.cli " + $item.Cmd
        $pinfo.RedirectStandardOutput = $true
        $pinfo.RedirectStandardError = $true
        $pinfo.UseShellExecute = $false
        $pinfo.CreateNoWindow = $true
        
        $p = [System.Diagnostics.Process]::Start($pinfo)
        $stdout = $p.StandardOutput.ReadToEnd()
        $stderr = $p.StandardError.ReadToEnd()
        $p.WaitForExit()
        $exitCode = $p.ExitCode

        Add-Content -Path $logFile -Value "`r`n=== Command: cleandownloads $($item.Cmd) (ExitCode: $exitCode) ===`r`n$stdout`r`n$stderr"

        if ($item.ExpectedExit -eq 0 -and $exitCode -ne 0) {
            throw "Command 'cleandownloads $($item.Cmd)' failed with exit code $exitCode. Error: $stderr"
        }

        # Check for unhandled tracebacks
        if ($stdout -match "Traceback \(most recent call last\):" -or $stderr -match "Traceback \(most recent call last\):") {
            throw "Command 'cleandownloads $($item.Cmd)' produced an unhandled Python crash traceback!"
        }

        Log-Step "[PASS] Command '$($item.Cmd)' executed cleanly ($($item.Desc))"
        $testResults.CommandsTested += $item.Cmd
    }

    Log-Step "[PASS] TEST CASE B PASSED: First launch and all CLI commands verified."
} catch {
    $err = $_.Exception.Message
    Log-Step "[FAIL] TEST CASE B FAILED: $err"
    $testResults.Passed = $false
    $testResults.Failures += $err
}

$testResults | ConvertTo-Json -Depth 5
