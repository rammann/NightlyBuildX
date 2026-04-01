# NightlyBuildX
Run regression test and unit tests for the OPALX (https://github.com/OPALX-project/OPALX) code.

## Usage
```
bash NightlyBuildX/scripts/run_tests --build <path-to-build> --tests <path-to-reg-tests> --unittests <on/off>
```
- `--build` specifies the build folder, can be `CPU` or `GPU`
- `--tests` specifies the path to the regression tests
- `--unittests` switches unit tests on (default) and off
- `--save` writes the report under `NightlyBuildX/report/runs_remote/<timestamp>/` instead of `report/runs/…` (see **Remote runs** below)

To run regression test inputs only (no compare/report):
```
bash NightlyBuildX/scripts/run_only_input --build <path-to-build> --input <path-to-reg-tests> [<name-of-test>]
```
- `--input` specifies the regression tests directory (or the regression-tests-x repo root)
- `<name-of-test>` is an optional test subfolder name (runs all if omitted)
- Outputs go to `NightlyBuildX/runs/...`; results are not validated against `reference/`

## Regression Tests
Any folder follwing the structure of https://github.com/rammann/regression-tests-x will work.

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
- `reference/*.stat` contains the reference stat file


## Output
This generates `NightlyBuildX/report/index.html`, which lists **local** runs (from `report/runs/`) and **remote** runs (from `report/runs_remote/`) in two columns. Each run links to its detailed HTML report. Static assets are under `report/assets/`.

### Remote runs
Use this when you run tests on another machine but want the summary in your local checkout.

1. On the remote machine, run the same `run_tests` command with **`--save`**. Output goes to `report/runs_remote/<timestamp>/` (logs, plots, `results.json`, per-run `index.html`).
2. Copy or commit that timestamped folder into your local repo’s `NightlyBuildX/report/runs_remote/`.
3. Locally, run `run_tests` once (any successful run regenerates the overview), or rely on the next run to refresh `report/index.html`. Open `report/index.html` to see both columns.

The `report/runs/` tree stays git-ignored (large local history). The `report/runs_remote/` tree is intended to be **tracked** so you can push remote summaries; only that subtree is meant for version control under `report/`.