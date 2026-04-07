# NightlyBuildX
Run regression test and unit tests for the OPALX (https://github.com/OPALX-project/OPALX) code.

## Usage

### Full regression suite
```
bash NightlyBuildX/scripts/run_tests --build <path-to-build> --tests <path-to-reg-tests> --unittests <on/off>
```
- `--build` specifies the build folder, can be `CPU` or `GPU`
- `--tests` specifies the path to the regression tests
- `--unittests` switches unit tests on (default) and off
- `--save` writes the report under `NightlyBuildX/report/runs_remote/<timestamp>/` instead of `report/runs/...` (see **Remote runs** below)

### Run a single input file (no reference validation)
```
bash NightlyBuildX/scripts/run --build <path-to-build> --input <path/to/file.in> [--mpi <ranks>]
```
- `--input` is the path to a single OPALX `.in` file
- `--mpi <ranks>` invokes `mpirun -n <ranks>`; omit for a direct (non-MPI) run
- Outputs go under `NightlyBuildX/runs/<stem>/` where `<stem>` is the input file name without extension
- **Run layout**:
  - `work/` — copy of the input file's directory; simulation outputs land here
  - `logs/run.out` — captured stdout/stderr
  - `plots/*.png` — one PNG per tracked stat column (all numeric columns in every discovered `.stat` file)
  - `run_report.pdf` — all plots assembled into a single PDF (best-effort)
- **Plots**: `plot_stat.py` writes one PNG per numeric column per stat stem using `s` or `t` as the x-axis. Requires **matplotlib** and `python3` on `PATH`.

You can run the plot helper directly on existing `.stat` files:
```
python3 NightlyBuildX/scripts/plot_stat.py --output /path/to/plots file1.stat file2.stat
python3 NightlyBuildX/scripts/plot_stat.py --output /path/to/plots --pdf out.pdf file1.stat
```

## Regression Tests
Any folder following the structure of https://github.com/rammann/regression-tests-x will work.

```
regression-tests-x/
└── RegressionTests/
    └─ Fodo-long/
        └── Fodo-long.in  
        └── Fodo-long.local  
        └── Fodo-long.rt 
        └── reference/
            └── Fodo-long.out
            └── Fodo-long.stat
    
```
- `*.in` is the input file
- `*.local` contains the run command
- `*.rt` contains the tracked stats and thresholds
- `reference/*.out` contains the reference output file
- `reference/*.stat` holds reference beam statistics. Use `reference/<name>.stat` for a single container, or `reference/<name>_c0.stat`, `reference/<name>_c1.stat`, ... for multi-container runs. Every `stat` line in `<name>.rt` is checked against **each** discovered `*.stat` stem (same variable list for all containers).


## Output
This generates `NightlyBuildX/report/index.html`, which lists **local** runs (from `report/runs/`) and **remote** runs (from `report/runs_remote/`) in two columns. Each run links to its detailed HTML report. Static assets are under `report/assets/`.

Per-simulation **beam / container parameters** in the detailed report (and in `results.json` as `beam_containers`) are parsed **best-effort** from the OPAL log copied to `<name>.out` (the `Beam::print` banners and `Beam[i]` lines from the run). If the run fails, the log is missing, or OPAL changes its print format, that section may be empty or incomplete; a warning is shown when the number of parsed beams does not match the number of reference `*.stat` stems.

### Remote runs
Use this when you run tests on another machine but want the summary in your local checkout.

1. On the remote machine, run the same `run_tests` command with **`--save`**. Output goes to `report/runs_remote/<timestamp>/` (logs, plots, `results.json`, per-run `index.html`).
2. **Git:** Add the full run directory under `NightlyBuildX/report/runs_remote/<timestamp>/`, including **`plots/**/*.png`**. The repo's `.gitignore` turns off the global `*.png` rule for paths under `report/runs_remote/`, so those images are meant to be **committed and pushed** like `results.json` and `index.html`. After `git add`, check `git status` shows the PNGs staged—not ignored.
3. Refresh the landing page so new or updated `runs_remote/` entries appear (no need to run the full suite):
   ```bash
   python3 NightlyBuildX/scripts/refresh_report_index.py
   ```
   Then open `NightlyBuildX/report/index.html`. A successful local `run_tests` run also regenerates the overview.

   Use a non-default report directory if needed:
   ```bash
   python3 NightlyBuildX/scripts/refresh_report_index.py --report-root /path/to/report
   ```

The `report/runs/` tree stays git-ignored (large local history). The `report/runs_remote/` tree is for **tracked** remote summaries, including plot PNGs so reports render after clone.
