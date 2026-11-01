# Contributing to CleanDownloads

Thank you for your interest in contributing to **CleanDownloads**! We welcome bug reports, feature suggestions, documentation enhancements, and pull requests.

---

## 🛠 Development Setup

### 1. Prerequisites
- **Operating System:** Windows 10 (Build 19045+) or Windows 11 (x64)
- **Python:** 3.11 or 3.12 (64-bit)
- **Git:** Installed and available on PATH
- **PowerShell:** Version 5.1+ or PowerShell 7+

### 2. Clone the Repository
```powershell
git clone https://github.com/mohdyasir5155/CleanDownloads.git
cd CleanDownloads
```

### 3. Create & Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 4. Install Dependencies
```powershell
pip install -e ".[dev]"
```

---

## 🧪 Testing & Quality Assurance

Before submitting any code, verify that all automated checks pass:

### 1. Run Unit & Security Test Suite
```powershell
pytest tests/ -v
```

### 2. Run Ruff Linter
```powershell
ruff check src/ tests/
```

### 3. Run Bandit Security Scanner
```powershell
bandit -r src/ -ll
```

### 4. Build Standalone Executable (Optional)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_executable.ps1
```

---

## 📐 Coding Standards & Safety Guidelines

- **Standard Library First:** Minimize external dependencies. Keep the core organizing engine fast, lightweight, and robust.
- **Strict Safety Invariants:** CleanDownloads enforces **14 strict safety invariants** (see [`SECURITY.md`](SECURITY.md)).
  - Never delete user files.
  - Never silently overwrite existing files (always generate numbered suffixes).
  - Never execute downloaded binaries.
  - Strict directory traversal containment.
- **Type Annotations:** All new Python functions, methods, and classes must include complete type hints.
- **Documentation:** Document new CLI arguments and configuration options in [`docs/USAGE.md`](docs/USAGE.md) and [`README.md`](README.md).

---

## 🚀 Pull Request Workflow

1. Fork the repository on GitHub.
2. Create a topic branch:
   ```powershell
   git checkout -b feature/my-new-feature
   ```
3. Commit your changes with descriptive messages:
   ```powershell
   git commit -m "feat(classifier): add support for .parquet files"
   ```
4. Push to your fork:
   ```powershell
   git push origin feature/my-new-feature
   ```
5. Open a Pull Request against `mohdyasir5155/CleanDownloads:main` using the PR template.

---

## 💬 Community & Discussions

- **Found a bug?** Submit an issue via our [Bug Report Template](https://github.com/mohdyasir5155/CleanDownloads/issues/new?template=bug_report.yml).
- **Have an idea?** Submit a [Feature Request](https://github.com/mohdyasir5155/CleanDownloads/issues/new?template=feature_request.yml).
- **Need help?** Start a discussion on GitHub Discussions!
