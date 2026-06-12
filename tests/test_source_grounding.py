from __future__ import annotations

import runpy
from collections.abc import Callable
from pathlib import Path


def test_source_grounding_manifest_is_current() -> None:
    namespace = runpy.run_path(str(Path("scripts/check_source_grounding.py")))
    main = namespace["main"]
    assert isinstance(main, Callable)
    assert main() == 0
