# Mini Spec: Modular Texture Pipeline

## 1. Purpose
Build a maintainable texture pipeline that supports both GUI and CLI usage with deterministic results, robust error handling, and recurring quality checks.

## 2. Scope
In scope:
1. Modularize generation, handcrafting, UI controls, and export behavior.
2. Provide beginner-friendly GUI defaults with advanced controls preserved.
3. Add CLI commands for single render, batch render, and quality inspection.
4. Add automated tests and repeatable visual quality review workflow.

Out of scope:
1. External rendering engines.
2. Machine-learning texture generation.
3. Asset packaging for specific game engines in this phase.

## 3. Non-Functional Requirements
1. Deterministic output for identical input parameters and seed.
2. Seamless tile continuity for generated textures.
3. Clear failure messages for invalid parameters.
4. Fast feedback loop for iteration and visual review.
5. No required paid tools; local workflow should run with standard browser + Python.

## 4. Proposed Module Architecture
### 4.1 Shared Contracts
- `TextureParams` contract:
  - `style: string`
  - `seed: int`
  - `size: int` (128/256/512)
  - `scale: int`
  - `octaves: int`
  - `roughness: float`
  - `contrast: float`
  - `grain: float`
  - `handcraft: float`
- Shared style/preset source:
  - `experiments/texture-presets.json` (single source of truth for style palettes and preset defaults)

### 4.2 GUI Modules
- `texture-lab.html`: structure only.
- `texture-lab.css`: styling only.
- `texture-lab.js` split into logical sections or files:
  1. `params` (read/validate/sync controls)
  2. `engine` (procedural generation)
  3. `handcraft` (paint layer + handcrafted pass)
  4. `ui-basic` (default controls and onboarding)
  5. `ui-advanced` (expert controls)
  6. `export` (filename and save behavior)
  7. `quality-preview` (tiled view overlays and hints)

### 4.3 CLI Modules
- `experiments/texture_cli.py`: argument parsing and command dispatch.
- `experiments/texture_core.py`: pure generation functions.
- `experiments/texture_quality.py`: seam and quality metrics.
- `experiments/texture_io.py`: export and report writing.

### 4.4 Test Modules
- `tests/test_params_validation.py`
- `tests/test_determinism.py`
- `tests/test_seam_integrity.py`
- `tests/test_cli_commands.py`
- `tests/test_quality_metrics.py`

## 5. CLI Command Spec
Command group:
1. `render`: generate one texture.
2. `batch`: generate multiple textures.
3. `inspect`: run quality checks and create a report/contact sheet.

Example command shapes:
```bash
python experiments/texture_cli.py render --style moss --seed 42 --size 256 --out textures
python experiments/texture_cli.py batch --style lava --count 24 --size 256 --preset game-ready --out textures
python experiments/texture_cli.py inspect --input textures --out textures/review
```

## 6. Quality Inspection Protocol
Quality checks are both automated and visual.

Automated checks:
1. Seam score: compare opposite edges and compute normalized mismatch.
2. Luminance spread: prevent flat/muddy output.
3. Contrast bounds: avoid crushed blacks/whites unless style requires it.

Visual checks:
1. Generate tiled previews/contact sheet for each batch.
2. Inspect at least 8 samples per style per major change.
3. Run this inspection at the end of each phase, not just final phase.

Artifacts:
- Reports saved to `textures/review/`.
- Include timestamp, command params, and pass/fail summary.

## 7. TDD Strategy
Mandatory cycle for each feature:
1. Write failing test.
2. Implement minimal passing code.
3. Refactor.
4. Re-run full test suite.
5. Run quality inspection on new outputs.

Priority test order:
1. Param validation tests.
2. Determinism tests.
3. Seam integrity tests.
4. CLI command and error-path tests.
5. Quality metrics threshold tests.

## 8. Robustness Requirements
1. Validate all numeric bounds and enum values.
2. Handle missing output directories by creating them safely.
3. Fail clearly on unsupported parameters.
4. Avoid partial writes by writing to temp and renaming where practical.
5. Preserve deterministic behavior across repeated runs.

## 9. Acceptance Criteria
1. GUI Basic mode is easy to use without technical knowledge.
2. Advanced mode remains available for fine control.
3. CLI supports render/batch/inspect and has clear `--help`.
4. Test suite passes consistently.
5. Quality reports and contact sheets are generated and reviewed.
6. Documentation explains 60-second quickstart for both GUI and CLI.

## 10. Delivery Artifacts
1. `plan.txt`
2. `mini-spec.md`
3. Refactored GUI modules/files
4. CLI implementation files
5. Test suite files
6. Updated README docs and quality reports
