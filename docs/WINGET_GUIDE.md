# WinGet Community Repository Submission & Testing Guide

This guide details the procedure for validating, testing, and submitting the **CleanDownloads** package to the official [Microsoft WinGet Community Repository (`microsoft/winget-pkgs`)](https://github.com/microsoft/winget-pkgs).

> [!IMPORTANT]
> **Submission Status:** The manifests generated in `winget/manifests/c/CleanDownloads/CleanDownloads/1.0.0/` are release-ready. The package is **not yet submitted or listed** on the official Microsoft WinGet Community repository. You must submit a pull request and await validation and approval from Microsoft moderators before users can install it via `winget install CleanDownloads.CleanDownloads`.

---

## 1. Manifest Architecture

CleanDownloads uses the multi-file manifest format conforming to WinGet Manifest Schema v1.6.0:

```
winget/manifests/c/CleanDownloads/CleanDownloads/1.0.0/
├── CleanDownloads.CleanDownloads.yaml               # Version manifest
├── CleanDownloads.CleanDownloads.installer.yaml     # Installer metadata, SHA256, switches
└── CleanDownloads.CleanDownloads.locale.en-US.yaml # English metadata, description, license
```

### Key Manifest Configuration

| Field | Value | Rationale |
| :--- | :--- | :--- |
| **PackageIdentifier** | `CleanDownloads.CleanDownloads` | Follows `<Publisher>.<Package>` convention. |
| **PackageVersion** | `1.0.0` | Semantic version matching git tag and PE info. |
| **InstallerType** | `inno` | Direct native support for Inno Setup 6. |
| **Scope** | `user` | Non-admin per-user installation into `%LOCALAPPDATA%\Programs`. |
| **Silent Switch** | `/VERYSILENT` | Headless installation without wizard UI. |
| **Custom Switches** | `/NORESTART /SUPPRESSMSGBOXES` | Prevents reboot prompts and suppresses message dialogs. |
| **ProductCode** | `{9B560C62-E764-4FD3-909E-D6A7862E8F48}_is1` | Registered uninstaller registry subkey under `HKCU`. |

---

## 2. Local Manifest Validation

Before submitting to `microsoft/winget-pkgs`, validate the manifest files locally using `winget validate`:

```powershell
winget validate --manifest winget\manifests\c\CleanDownloads\CleanDownloads\1.0.0\
```

Expected output:
```text
Manifest validation succeeded.
```

If any errors occur, `winget validate` will output the exact JSON Schema violation (e.g., missing required fields, invalid URL formats, or regex mismatch).

---

## 3. Local Installation Testing

Test installing the package from your local manifest files:

```powershell
# 1. Test installation using local manifest directory
winget test --manifest winget\manifests\c\CleanDownloads\CleanDownloads\1.0.0\

# 2. Verify command line availability
cleandownloads --version

# 3. Test uninstallation
winget uninstall --id CleanDownloads.CleanDownloads
```

---

## 4. Windows Sandbox Isolation Testing

To ensure the installer works on a virgin Windows installation without pre-installed runtimes:

1. Open **Windows Sandbox** (run `windows-sandbox.exe`).
2. Share the repository folder or upload the installer and manifests.
3. In PowerShell inside Sandbox, run:
   ```powershell
   # Validate installer execution in pure non-admin context
   Start-Process -FilePath "CleanDownloads-Setup-1.0.0.exe" -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART" -Wait
   
   # Verify PATH update and execution
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";$env:Path"
   cleandownloads.exe --help
   ```

---

## 5. Community Repository Submission (Pull Request)

### Method A: Using `wingetcreate` (Automated CLI)

The easiest method is using Microsoft's official `wingetcreate` tool:

1. Install `wingetcreate`:
   ```powershell
   winget install Microsoft.WingetCreate
   ```
2. Generate a GitHub Personal Access Token (PAT) with `public_repo` scope.
3. Submit the release directly:
   ```powershell
   wingetcreate submit `
     --token "<YOUR_GITHUB_PAT>" `
     --urls "https://github.com/cleandownloads/CleanDownloads/releases/download/v1.0.0/CleanDownloads-Setup-1.0.0.exe"
   ```

### Method B: Manual Git Pull Request

1. Fork the official [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) repository.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<YOUR_USERNAME>/winget-pkgs.git
   cd winget-pkgs
   git checkout -b add-cleandownloads-1.0.0
   ```
3. Copy the manifest folder:
   ```powershell
   Copy-Item -Recurse `
     "winget\manifests\c\CleanDownloads\CleanDownloads\1.0.0" `
     "manifests\c\CleanDownloads\CleanDownloads\"
   ```
4. Validate the manifests inside the repository clone:
   ```powershell
   winget validate --manifest manifests\c\CleanDownloads\CleanDownloads\1.0.0\
   ```
5. Commit and push:
   ```bash
   git add manifests/c/CleanDownloads/CleanDownloads/1.0.0
   git commit -m "Add CleanDownloads version 1.0.0"
   git push origin add-cleandownloads-1.0.0
   ```
6. Open a Pull Request against `microsoft/winget-pkgs:master`.
7. Monitor automated CI checks (`Azure Pipelines` / `GitHub Actions`) for schema validation and sandbox installation tests.

---

## 6. Version Update Procedure (Subsequent Releases)

When releasing a new version (e.g. `1.1.0`):

1. Tag and draft release on GitHub (`v1.1.0`).
2. Build installer with `scripts\build_installer.ps1 -Version 1.1.0`.
3. Update `wingetcreate`:
   ```powershell
   wingetcreate update CleanDownloads.CleanDownloads `
     --urls "https://github.com/cleandownloads/CleanDownloads/releases/download/v1.1.0/CleanDownloads-Setup-1.1.0.exe" `
     --version 1.1.0 `
     --token "<YOUR_GITHUB_PAT>"
   ```
4. Microsoft bot will automatically test the upgrade in an Azure VM sandbox and merge upon passing.
