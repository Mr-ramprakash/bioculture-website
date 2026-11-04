"""Load the project-root Vercel function used by the deployed project."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_root_vercel_entry():
    project_root = Path(__file__).resolve().parents[2]
    entry_path = project_root / "api" / "index.py"
    spec = importlib.util.spec_from_file_location("root_vercel_api_entry", entry_path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load project-root Vercel API entry point")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
