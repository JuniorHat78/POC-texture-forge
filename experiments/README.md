# Texture Experiments

This folder now has two parallel workflows:

1. GUI workflow for fast visual iteration.
2. CLI workflow for deterministic, repeatable asset generation.

## Quickstart

### GUI (beginner-friendly)
1. Open `experiments/texture-lab.html` in your browser.
2. Leave `Workflow Mode` on `Basic (Recommended)`.
3. Adjust:
   - Style
   - Seed
   - Texture Size
   - Variation
   - Handcraft Strength
4. Click `Render` and `Export PNG`.
5. Save into `textures/`.
6. In Advanced mode, use `Undo Paint` / `Redo Paint` or hotkeys:
   - `Ctrl/Cmd+Z`: undo paint
   - `Ctrl/Cmd+Shift+Z` or `Ctrl/Cmd+Y`: redo paint
   - `R`: render, `H`: handcrafted pass

### CLI (deterministic + batch-friendly)
```bash
python -m experiments.texture_cli render --style moss --seed 42 --size 256 --preset game-ready --out textures
python -m experiments.texture_cli batch --style lava --seed 3000 --size 256 --count 12 --preset game-ready --out textures/batch_lava
python -m experiments.texture_cli inspect --input textures/batch_lava --out textures/review/lava_batch --limit 12 --columns 4
```

Each generated PNG now includes a sidecar JSON (`same-name.json`) with full params for inspection and auditability.

### CLI safety flags
```bash
python -m experiments.texture_cli render --style moss --seed 42 --size 256 --dry-run --out textures
python -m experiments.texture_cli batch --style lava --seed 3000 --size 256 --count 8 --dry-run --out textures/batch_lava
python -m experiments.texture_cli inspect --input textures/batch_lava --out textures/review/lava_batch --strict
python -m experiments.texture_cli inspect --input textures/batch_lava --out textures/review/lava_batch --quality-profile strict --strict --timestamped
```

### CLI matrix mode
```bash
python -m experiments.texture_cli matrix --styles all --count-per-style 2 --size 256 --seed 5000 --out textures/matrix
python -m experiments.texture_cli matrix --styles moss,lava,ice --count-per-style 3 --size 256 --out textures/matrix_subset
```

### End-to-end release gate
```bash
python -m experiments.release_quality_gate --styles all --count-per-style 1 --size 128 --quality-profile default --allow-failures 0
```

This single command:

1. Runs unit tests (unless `--skip-tests` is provided).
2. Generates a deterministic matrix sample set.
3. Runs timestamped quality inspection.
4. Writes a machine-readable `gate-report.json`.
5. Returns non-zero exit code on gate failure.

## Architecture (Phase 0/1)

Core modules under `experiments/texture_pipeline/`:

1. `contract.py`: typed parameter contract + validation + file-name parsing.
2. `presets.py`: shared defaults/styles/presets from `texture-presets.json`.
3. `core.py`: deterministic procedural generation and handcrafted pass.
4. `quality.py`: seam and luminance metrics + contact sheet composition + configurable thresholds.
5. `io.py`: atomic JSON write and PNG encoding.

CLI entry:

1. `experiments/texture_cli.py`

GUI modules:

1. `experiments/texture-lab.shared.js`: DOM/state utilities and style definitions.
2. `experiments/texture-lab.params.js`: parameter mapping, defaults, and Basic/Advanced mode behavior.
3. `experiments/texture-lab.engine.js`: procedural generation, render pipeline, and export.
4. `experiments/texture-lab.handcraft.js`: seamless painting and handcrafted layer logic.
5. `experiments/texture-lab.ui.js`: event wiring and app bootstrap.
6. `experiments/texture-lab.worker.js`: background worker render path for larger textures (512x512).

## Test Suite

Run all tests:
```bash
python -m unittest discover -s tests -v
```

Current TDD coverage:

1. Parameter validation.
2. Determinism by seed.
3. Seam quality threshold.
4. CLI render/batch/matrix/inspect behavior.
5. CLI error paths and strict-quality failures.
6. GUI defaults parity with shared contract.
7. Release quality gate pass/fail behavior and path handling.

CI automation:

1. `.github/workflows/texture-quality-gate.yml` runs the release gate on push/PR (tests included by gate command).
2. Gate artifacts are uploaded for visual review (`textures/review/gates`, `textures/gate_samples`).

## Quality Review Cadence

Run a quality checkpoint:

1. Generate a batch or matrix with fixed seed range.
2. Run `inspect` with a quality profile to evaluate actual PNG pixels and produce:
   - `quality-report.json`
   - `contact-sheet.png`
3. Use `--timestamped` when you want historical artifacts per run.
4. Inspect contact sheet visually.
5. Review seam/contrast metrics in report summary, including:
   - `quality_profile`
   - `quality_thresholds`
   - `failed_files`
   - `style_breakdown`
