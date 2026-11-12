"""Build the React frontend and package the desktop executable with PyInstaller."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"


def run(cmd: list[str], cwd: Path) -> None:
    printable = " ".join(str(part) for part in cmd)
    print(f"+ {printable}", flush=True)
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        raise SystemExit(f"command failed with exit code {result.returncode}: {printable}")


def npm_executable() -> list[str]:
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm not found in PATH. Install Node.js 18+ and retry.")
    if os.name == "nt" and npm.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", npm]
    return [npm]


def build_frontend() -> None:
    npm = npm_executable()

    if not (FRONTEND / "node_modules").is_dir():
        lock = FRONTEND / "package-lock.json"
        run([*npm, "ci" if lock.is_file() else "install"], FRONTEND)

    run([*npm, "run", "build"], FRONTEND)

    index = FRONTEND / "dist" / "index.html"
    if not index.is_file():
        raise SystemExit(f"Frontend build output is missing: {index}")


def build_executable() -> Path:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        raise SystemExit(
            'PyInstaller is not installed. Run: pip install -e ".[dev,build]"'
        ) from None

    sep = ";" if os.name == "nt" else ":"
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--name",
        "PriceAggregator",
        "--paths",
        str(BACKEND),
        "--collect-all",
        "webview",
        "--collect-all",
        "uvicorn",
        "--collect-all",
        "playwright",
        "--add-data",
        f"{FRONTEND / 'dist'}{sep}frontend/dist",
        "--add-data",
        f"{BACKEND / 'plugins'}{sep}backend/plugins",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        "--specpath",
        str(ROOT / "build"),
        str(BACKEND / "app" / "main.py"),
    ]
    run(args, ROOT)

    exe = ROOT / "dist" / ("PriceAggregator.exe" if os.name == "nt" else "PriceAggregator")
    if not exe.is_file():
        raise SystemExit(f"PyInstaller finished but the executable is missing: {exe}")
    return exe


def main() -> None:
    build_frontend()
    exe = build_executable()
    print(f"\nBuilt: {exe}")


if __name__ == "__main__":
    main()
