from __future__ import annotations

import subprocess
import sys
from os import environ

import warpline


def test_package_has_version() -> None:
    assert warpline.__version__ == "1.1.0"


def test_cli_version() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "warpline.cli", "--version"],
        check=True,
        env={**environ, "PYTHONPATH": "src"},
        text=True,
        stdout=subprocess.PIPE,
    )
    assert completed.stdout.strip() == "warpline 1.1.0"
