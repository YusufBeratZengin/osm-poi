"""Alias for make-demo.py."""

import importlib.util
from pathlib import Path

_script = Path(__file__).resolve().parent / "make-demo.py"
_spec = importlib.util.spec_from_file_location("make_demo", _script)
if _spec and _spec.loader:
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

if __name__ == "__main__":
    _mod.main()
