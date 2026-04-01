#!/usr/bin/env python3
"""Regenerate report/index.html (and assets) from existing runs/ and runs_remote/."""

import argparse
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

from OpalRegressionTests.sitegen import update_overview, write_report_assets


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild the report landing page (index.html) without running tests.",
    )
    parser.add_argument(
        "--report-root",
        type=str,
        default=None,
        help="Directory containing runs/, runs_remote/, index.html (default: NightlyBuildX/report next to this script)",
    )
    args = parser.parse_args()
    if args.report_root:
        report_root = os.path.abspath(args.report_root)
    else:
        nightlybuildx_dir = os.path.dirname(_script_dir)
        report_root = os.path.join(nightlybuildx_dir, "report")
    os.makedirs(report_root, exist_ok=True)
    write_report_assets(report_root)
    update_overview(report_root)
    print(f"Wrote {os.path.join(report_root, 'index.html')}")


if __name__ == "__main__":
    main()
