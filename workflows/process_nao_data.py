#!/usr/bin/env python3
"""Compatibility entry point for the generalized modes-of-variability runner."""

from __future__ import annotations

import sys

try:
    from workflows.run_modes_of_variability import main
except ModuleNotFoundError:
    from run_modes_of_variability import main


if "--modes" not in sys.argv:
    sys.argv.extend(["--modes", "NAO"])
if "--legacy-nao-layout" not in sys.argv:
    sys.argv.append("--legacy-nao-layout")

if __name__ == "__main__":
    main()
