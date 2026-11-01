# Installation Guide — CleanDownloads

CleanDownloads is designed for fast, seamless setup on Windows with **zero administrative privileges required**.

---

## ⚡ 1. PowerShell Bootstrapper (Recommended)

Open **PowerShell** (no admin rights needed) and run:

```powershell
irm https://raw.githubusercontent.com/mohdyasir5155/CleanDownloads/main/install.ps1 | iex
```

### What the Bootstrapper Does:
1. Detects Windows x64 environment in standard user context.
2. Queries the latest GitHub release over HTTPS.
3. Downloads the setup installer to a temporary location.
4. Cryptographically verifies the mandatory SHA-256 hash against release `checksums.txt` (fails closed if missing or mismatched).
5. If GitHub CLI (`gh`) is available, verifies build provenance attestations against the repository (`gh attestation verify`).
6. Executes the silent non-admin installer into `%LOCALAPPDATA%\Programs\CleanDownloads`.
7. Appends the binary folder to user `PATH` (`HKCU\Environment\Path`) and broadcasts environment change.
8. Verifies `cleandownloads --version`.

> [!NOTE]
> **Authenticode Verification**: Authenticode verification is opt-in via `-RequireSignature` for enterprise or corporate environments requiring code signing certificate checks. By default, release binaries are verified via mandatory SHA-256 checksums and GitHub Artifact Attestation.

---

## 💻 2. Windows Setup Wizard (Inno Setup)

1. Download `CleanDownloads-Setup-1.0.0.exe` from [GitHub Releases](https://github.com/mohdyasir5155/CleanDownloads/releases/latest).
2. (Optional) Check SHA-256 integrity:
   ```powershell
   Get-FileHash .\CleanDownloads-Setup-1.0.0.exe -Algorithm SHA256
   ```
3. Run the installer interactively or headless:
   ```powershell
   .\CleanDownloads-Setup-1.0.0.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
   ```

---

## 📦 3. Microsoft WinGet Community Package

> [!NOTE]
> WinGet package manifests are currently submitted under `CleanDownloads.CleanDownloads` and awaiting community review in `microsoft/winget-pkgs`.

```powershell
winget install CleanDownloads.CleanDownloads
```

---

## 🚀 4. Portable Standalone Binary

1. Download `cleandownloads.exe` from [GitHub Releases](https://github.com/mohdyasir5155/CleanDownloads/releases/latest).
2. Move it to any folder included in your system or user `PATH`.
3. No Python installation or runtime is required.

---

## 🛠 5. Install from Source

If you prefer to install from source for development:

```powershell
git clone https://github.com/mohdyasir5155/CleanDownloads.git
cd CleanDownloads

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

cleandownloads --version
```

---

## 🗑 Uninstallation

CleanDownloads provides a clean, non-destructive uninstaller that removes all launchers, scheduled tasks, and PATH entries without touching your personal files:

```powershell
# Option 1: Native Windows uninstaller
& "$env:LOCALAPPDATA\Programs\CleanDownloads\unins000.exe" /VERYSILENT

# Option 2: PowerShell script
powershell -ExecutionPolicy Bypass -File uninstall.ps1

# Option 3: Via Windows Settings
# Installed apps -> CleanDownloads -> Uninstall
```
