"""
Build script: compile the FastAPI backend into a standalone executable using PyInstaller.
The binary is placed in src-tauri/binaries/ with the correct Tauri target triple name.

Usage: python build.py
"""

import platform
import subprocess
import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
PROJECT_ROOT = BACKEND_DIR.parent
TAURI_BINARIES = PROJECT_ROOT / "src-tauri" / "binaries"

BINARY_NAME = "vibetaff-backend"


def get_target_triple() -> str:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        arch = "aarch64"
    elif machine in ("x86_64", "amd64"):
        arch = "x86_64"
    else:
        arch = machine

    system = platform.system().lower()
    if system == "darwin":
        return f"{arch}-apple-darwin"
    elif system == "linux":
        return f"{arch}-unknown-linux-gnu"
    elif system == "windows":
        return f"{arch}-pc-windows-msvc"
    else:
        return f"{arch}-unknown-{system}"


def build():
    target_triple = get_target_triple()
    output_name = f"{BINARY_NAME}-{target_triple}"
    print(f"Building for target: {target_triple}")
    print(f"Output binary: {output_name}")

    pyinstaller_args = [
        "pyinstaller",
        "--onefile",
        "--name", BINARY_NAME,
        "--distpath", str(BACKEND_DIR / "dist"),
        "--workpath", str(BACKEND_DIR / "build_temp"),
        "--specpath", str(BACKEND_DIR),
        "--noconfirm",
        "--clean",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.loops.asyncio",
        "--hidden-import", "multipart",
        "--hidden-import", "dotenv",
        "--collect-data", "sentence_transformers",
        "--collect-data", "lancedb",
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PIL",
        "--exclude-module", "IPython",
        "--exclude-module", "notebook",
        "--exclude-module", "pytest",
        str(BACKEND_DIR / "main.py"),
    ]

    print("\nRunning PyInstaller...")
    result = subprocess.run(pyinstaller_args, cwd=str(BACKEND_DIR))
    if result.returncode != 0:
        print("PyInstaller build FAILED")
        return False

    source = BACKEND_DIR / "dist" / BINARY_NAME
    if not source.exists():
        print(f"Binary not found at {source}")
        return False

    TAURI_BINARIES.mkdir(parents=True, exist_ok=True)
    dest = TAURI_BINARIES / output_name
    shutil.copy2(str(source), str(dest))
    dest.chmod(0o755)

    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"\nBinary copied to: {dest}")
    print(f"Size: {size_mb:.1f} MB")
    print("Build SUCCESS")

    build_temp = BACKEND_DIR / "build_temp"
    if build_temp.exists():
        shutil.rmtree(build_temp)

    return True


if __name__ == "__main__":
    build()
