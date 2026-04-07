#!/usr/bin/env python3
"""
Plot all numeric columns from OPALX ASCII SDDS .stat file(s).
One PNG per (column, stat-stem) pair. X-axis: 's' or 't' column.
"""

from __future__ import annotations

import argparse
import os
import sys

PLOT_FIGSIZE_IN = (10.0, 5.625)
PLOT_DPI = 240


def _setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.style.use("bmh")
    return plt


def _read_stat_header(lines: list[str]) -> tuple[dict, int]:
    header: dict = {"columns": {}, "parameters": {}}
    i = 0
    while i < len(lines):
        line = lines[i]
        if "&column" in line:
            block = ""
            while True:
                block += line
                if "&end" in line:
                    break
                i += 1
                line = lines[i]
            parts = block.split("name=")
            if len(parts) >= 2:
                name = parts[1].split(",")[0].strip()
                unit = ""
                if "units=" in block:
                    unit = block.split("units=")[1].split(",")[0].strip()
                header["columns"][name] = {
                    "units": unit,
                    "column": len(header["columns"]),
                }
        elif "&parameter" in line:
            block = ""
            while True:
                block += line
                if "&end" in line:
                    break
                i += 1
                line = lines[i]
            if "name=" in block:
                name = block.split("name=")[1].split(",")[0].strip()
                header["parameters"][name] = {"row": len(header["parameters"])}
        elif "&data" in line:
            while "&end" not in line:
                i += 1
                line = lines[i]
            i += 1
            break
        i += 1
    return header, i


def read_stat(path: str) -> tuple[dict[str, list[float]], dict[str, str]]:
    """Parse .stat file, return (data, units) dicts keyed by column name."""
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = [ln.rstrip("\n") for ln in f]

    header, data_start = _read_stat_header(lines)
    if not header["columns"]:
        raise ValueError(f"No columns in stat header: {path}")

    num_scalars = len(header["parameters"])
    col_items = sorted(header["columns"].items(), key=lambda kv: kv[1]["column"])
    col_names = [n for n, _ in col_items]
    units = {n: info.get("units", "") for n, info in col_items}

    rows: list[list[float]] = []
    for line in lines[data_start + num_scalars :]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < len(col_names):
            continue
        try:
            rows.append([float(p) for p in parts[: len(col_names)]])
        except ValueError:
            continue

    if not rows:
        raise ValueError(f"No data rows parsed: {path}")

    data: dict[str, list[float]] = {n: [] for n in col_names}
    for row in rows:
        for n, v in zip(col_names, row):
            data[n].append(v)
    return data, units


def _x_axis(data: dict[str, list[float]], units: dict[str, str]) -> tuple[str, list[float], str]:
    for candidate in ("s", "t"):
        if candidate in data:
            return candidate, data[candidate], units.get(candidate, "")
    raise ValueError("No 's' or 't' column for x-axis")


def plot_stat_file(stat_path: str, output_dir: str, dpi: int = PLOT_DPI) -> int:
    try:
        data, units = read_stat(stat_path)
    except (OSError, ValueError) as e:
        print(f"WARN: skip {stat_path}: {e}", file=sys.stderr)
        return 0

    try:
        x_name, x_vals, x_unit = _x_axis(data, units)
    except ValueError as e:
        print(f"WARN: skip {stat_path}: {e}", file=sys.stderr)
        return 0

    try:
        plt = _setup_mpl()
    except ImportError as e:
        print(f"ERROR: matplotlib required: {e}", file=sys.stderr)
        return 1

    os.makedirs(output_dir, exist_ok=True)
    stem = os.path.basename(stat_path)
    if stem.endswith(".stat"):
        stem = stem[: -len(".stat")]

    xlab = f"{x_name} [{x_unit}]" if x_unit else x_name
    skip = {x_name}
    n_ok = 0

    for col, y_vals in data.items():
        if col in skip:
            continue
        if len(y_vals) != len(x_vals):
            continue
        try:
            _ = [float(v) for v in y_vals]
        except (TypeError, ValueError):
            continue

        y_unit = units.get(col, "")
        ylab = f"{col} [{y_unit}]" if y_unit else col

        fig, ax = plt.subplots(figsize=PLOT_FIGSIZE_IN)
        ax.plot(x_vals, y_vals, lw=1.5)
        ax.set_xlabel(xlab)
        ax.set_ylabel(ylab)
        ax.set_title(f"{stem}: {col}")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        safe_col = col.replace("/", "_").replace("\\", "_")
        out_png = os.path.join(output_dir, f"{safe_col}_{stem}.png")
        fig.savefig(out_png, dpi=dpi)
        plt.close(fig)
        n_ok += 1

    print(f"Wrote {n_ok} plot(s) for {stat_path} -> {output_dir}")
    return 0


def build_pdf(plots_dir: str, output_path: str, run_label: str = "") -> int:
    """Assemble all PNGs under plots_dir into a single PDF (best-effort)."""
    import glob
    import math
    import datetime

    try:
        plt = _setup_mpl()
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.gridspec import GridSpec
    except ImportError as e:
        print(f"ERROR: matplotlib required: {e}", file=sys.stderr)
        return 1

    pngs = sorted(glob.glob(os.path.join(plots_dir, "*.png")))
    if not pngs:
        print(f"WARN: no PNGs found in {plots_dir}", file=sys.stderr)
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with PdfPages(output_path) as pdf:
        # Cover page
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        ax.text(0.5, 0.55, "OPALX run report", ha="center", va="center",
                fontsize=18, fontweight="bold")
        ax.text(0.5, 0.45, run_label or os.path.basename(plots_dir),
                ha="center", va="center", fontsize=12)
        ax.text(0.5, 0.36, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                ha="center", va="center", fontsize=10, color="gray")
        pdf.savefig(fig, bbox_inches="tight", dpi=150)
        plt.close(fig)

        # Grid pages (up to 12 plots per page)
        per_page = 12
        ncols = 4
        for page_start in range(0, len(pngs), per_page):
            chunk = pngs[page_start : page_start + per_page]
            n = len(chunk)
            nrows = int(math.ceil(n / ncols))
            fig = plt.figure(figsize=(11, 8.5))
            gs = GridSpec(nrows, ncols, figure=fig,
                          top=0.96, bottom=0.02, left=0.02, right=0.98,
                          hspace=0.4, wspace=0.1)
            for i, png in enumerate(chunk):
                r, c = divmod(i, ncols)
                ax = fig.add_subplot(gs[r, c])
                ax.imshow(plt.imread(png))
                ax.axis("off")
                ax.set_title(os.path.basename(png).replace(".png", ""),
                             fontsize=4.5)
            pdf.savefig(fig, bbox_inches="tight", dpi=150)
            plt.close(fig)

    print(f"Wrote PDF: {output_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Plot all numeric columns from OPALX .stat file(s). "
                    "One PNG per column per file."
    )
    p.add_argument("--output", "-o", required=True,
                   help="Output directory for PNG files")
    p.add_argument("--dpi", type=int, default=PLOT_DPI,
                   help=f"PNG resolution (default: {PLOT_DPI})")
    p.add_argument("--pdf", metavar="PATH",
                   help="Also assemble all PNGs into a PDF at this path")
    p.add_argument("stat_files", nargs="+", help="One or more .stat files")
    args = p.parse_args()

    out = os.path.abspath(args.output)
    rc = 0
    for sf in args.stat_files:
        sf = os.path.abspath(sf)
        if not os.path.isfile(sf):
            print(f"WARN: not a file: {sf}", file=sys.stderr)
            rc = 1
            continue
        r = plot_stat_file(sf, out, dpi=args.dpi)
        if r != 0:
            rc = r

    if args.pdf:
        r = build_pdf(out, os.path.abspath(args.pdf))
        if r != 0:
            rc = r

    return rc


if __name__ == "__main__":
    sys.exit(main())
