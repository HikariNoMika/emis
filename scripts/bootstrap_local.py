#!/usr/bin/env python3
"""One-command setup for a clean local (SQLite) install.

Usage, from the repository root:
    python scripts/bootstrap_local.py

It creates backend/venv, installs requirements, writes backend/.env with a
SQLite database URL and fresh random secrets, then runs seed.py to create the
schema, administrator account and measurement catalogue.

An existing backend/.env or database is never overwritten.
"""

import os
import re
import secrets
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
VENV_DIR = BACKEND / "venv"
PYTHON = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(args, cwd):
    print("\n> " + " ".join(str(arg) for arg in args))
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def write_env_if_missing():
    env_path = BACKEND / ".env"
    if env_path.exists():
        print(f"\nKeeping existing {env_path}")
        return

    text = (BACKEND / ".env.example").read_text(encoding="utf-8")
    replacements = {
        r"^DATABASE_URL=.*$": "DATABASE_URL=sqlite:///emis_dev.db",
        r"^SECRET_KEY=.*$": "SECRET_KEY=" + secrets.token_hex(32),
        r"^JWT_SECRET_KEY=.*$": "JWT_SECRET_KEY=" + secrets.token_hex(32),
    }
    for pattern, value in replacements.items():
        text, count = re.subn(pattern, value, text, flags=re.MULTILINE)
        if count == 0:
            text += "\n" + value + "\n"
    env_path.write_text(text, encoding="utf-8")
    print(f"\nCreated {env_path} (SQLite + fresh secrets)")


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("Python 3.11 or newer is required.")

    if not PYTHON.exists():
        print("\nCreating virtual environment...")
        venv.create(VENV_DIR, with_pip=True)

    run([PYTHON, "-m", "pip", "install", "-r", "requirements.txt"], BACKEND)
    write_env_if_missing()
    run([PYTHON, "seed.py"], BACKEND)

    print("\nBackend ready. Start the servers in two terminals:")
    print(f"  cd {BACKEND}")
    print(f"  {PYTHON} run.py            # http://localhost:5000")
    print("  cd frontend")
    print("  npm install")
    print("  npm run dev                # http://localhost:5173")
    print("\nDefault login: admin / ChangeThisPassword123!")
    print("Set ADMIN_PASSWORD in backend/.env before bootstrapping to change it.")


if __name__ == "__main__":
    main()
