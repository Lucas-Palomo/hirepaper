#!/usr/bin/env python3
"""Build a single binary of hirepaper via PyInstaller.

Usage:
    .venv/bin/python build.py

The executable is written to dist/hirepaper.
"""

import PyInstaller.__main__
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

DATA_FILES = [
    (str(ROOT / "templates"), "templates"),
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "locale"), "locale"),
]

HIDDEN_IMPORTS = [
    "litellm.litellm_core_utils",
    "litellm.litellm_core_utils.tokenizers",
    "litellm.utils",
]

PyInstaller.__main__.run(
    [
        str(ROOT / "src" / "hirepaper" / "__main__.py"),
        "--name=hirepaper",
        "--onefile",
        "--clean",
        "--distpath=" + str(DIST),
        "--workpath=" + str(ROOT / "build" / "pyinstaller"),
        "--specpath=" + str(ROOT / "build"),
        "--log-level=WARN",
        "--collect-all=litellm",
    ]
    + [f"--add-data={src}:{dst}" for src, dst in DATA_FILES]
    + [f"--hidden-import={mod}" for mod in HIDDEN_IMPORTS]
)
