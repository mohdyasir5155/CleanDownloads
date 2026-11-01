# Reproducible Build Guide — CleanDownloads

This document outlines the step-by-step procedure for producing bit-accurate, verifiable, and reproducible distribution artifacts for **CleanDownloads** on Microsoft Windows x64.

---

## 1. System Requirements & Build Toolchain

To reproduce the exact production binaries and installer, the following toolchain is required:

| Component | Required Version | Purpose |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 x64 (Build 19045+) | Target execution environment |
| **Python** | 3.12.x (64-bit) | CPython runtime for PyInstaller compilation |
| **PyInstaller** | 6.22.x | Standalone PE bundling engine |
| **Inno Setup** | 6.7.x | Windows installer compiler (`iscc.exe`) |
| **PowerShell** | 5.1+ or PowerShell 7+ | Build script automation |
| **Code Signing Certificate** | Authenticode SHA-256 | Windows SmartScreen & Application Control compliance |

---

## 2. Directory Layout & Storage Separation

CleanDownloads strictly separates application binaries from user configuration and runtime state:

- **Binaries & Assets:**
  - Standalone executable: `dist/cleandownloads.exe`
  - Setup installer: `dist/CleanDownloads-Setup-<version>.exe`
  - Default install directory: `%LOCALAPPDATA%\Programs\CleanDownloads\`
- **User Configuration & State (Outside Executable Directory):**
  - Path: `%LOCALAPPDATA%\CleanDownloads\`
  - Config: `%LOCALAPPDATA%\CleanDownloads\config.json`
  - Operation Database: `%LOCALAPPDATA%\CleanDownloads\history.db`
  - Log Files: `%LOCALAPPDATA%\CleanDownloads\logs\`

> [!IMPORTANT]
> The executable directory does **not** store any user state. Upgrades and uninstallation replace or remove binary files without touching `%LOCALAPPDATA%\CleanDownloads\config.json` or `%LOCALAPPDATA%\CleanDownloads\history.db`.

---

## 3. Step-by-Step Reproducible Build Instructions

### Step 1: Clone Repository and Enter Workspace

```powershell
git clone https://github.com/mohdy/CleanDownloads.git
cd CleanDownloads
```

### Step 2: Create Isolated Virtual Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pyinstaller rich
```

### Step 3: Install Inno Setup 6

If Inno Setup 6 is not installed on your system:

```powershell
# Option A: via winget
winget install --id JRSoftware.InnoSetup --scope user --silent

# Option B: via helper script
powershell -ExecutionPolicy Bypass -File scripts\setup_innosetup.ps1
```

### Step 4: Build Standalone Executable (`cleandownloads.exe`)

The executable build uses `cleandownloads.spec` and Windows PE resource metadata from `version_info.txt`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_executable.ps1 -Version "1.0.0"
```

This step executes:
1. Validates Python environment and `pyinstaller`.
2. Compiles `src/cleandownloads/cli.py` into a single-file executable `dist/cleandownloads.exe`.
3. Embeds `version_info.txt` defining `FileVersion=1.0.0.0`, `ProductVersion=1.0.0.0`, `CompanyName=CleanDownloads`.
4. Embeds `config/default_rules.json` as bundled internal data.
5. Signs the binary with an available Authenticode certificate.
6. Computes and displays the SHA-256 hash.

### Step 5: Build Inno Setup Windows Installer

Compile the Inno Setup script `installer/CleanDownloads.iss`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -Version "1.0.0"
```

This step executes:
1. Locates `iscc.exe`.
2. Compiles `installer/CleanDownloads.iss` with LZMA2 solid compression.
3. Packages `cleandownloads.exe`, `LICENSE.txt`, and `README.md`.
4. Injects uninstaller registration and user PATH update logic.
5. Signs `CleanDownloads-Setup-1.0.0.exe` with Authenticode SHA-256.
6. Writes updated checksums to `dist/checksums.txt`.

---

## 4. Verifying Build Outputs

Verify file properties, digital signatures, and hashes:

```powershell
# 1. Verify executable version and help menu
.\dist\cleandownloads.exe --version
.\dist\cleandownloads.exe --help

# 2. Verify digital signature
Get-AuthenticodeSignature .\dist\cleandownloads.exe
Get-AuthenticodeSignature .\dist\CleanDownloads-Setup-1.0.0.exe

# 3. Verify SHA-256 integrity
Get-FileHash .\dist\cleandownloads.exe -Algorithm SHA256
Get-FileHash .\dist\CleanDownloads-Setup-1.0.0.exe -Algorithm SHA256
```

---

## 5. Security & Signing Considerations

On modern Windows (Windows 11 Build 26100+, Smart App Control, and Windows Defender Application Control):
- **Development/CI Signing:** Self-signed code signing certificates can be generated using `New-SelfSignedCertificate -Type CodeSigningCert`.
- **Production Distribution Signing:** Production releases submitted to GitHub Releases and Microsoft WinGet Community Repository must be signed using an EV (Extended Validation) code signing certificate or trusted CA certificate (e.g., Certum, DigiCert, Sectigo) or GitHub Attestations.
