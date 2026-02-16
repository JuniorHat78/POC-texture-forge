# Textures Folder

Drop exported texture files here.

Recommended naming:
- `style-seed-size-hXX.png`
- Example: `lava-31872491-256-h35.png`

Starter workflow:
1. Open `experiments/texture-lab.html` in your browser.
2. Randomize or tweak settings.
3. Click `Export PNG`.
4. Save into this `textures/` folder.

CLI workflow:
1. `python -m experiments.texture_cli batch --style moss --seed 5000 --size 256 --count 8 --out textures/moss_batch`
2. `python -m experiments.texture_cli inspect --input textures/moss_batch --out textures/review/moss_batch`
3. Optional stricter gate: `python -m experiments.texture_cli inspect --input textures/moss_batch --out textures/review/moss_batch --quality-profile strict --strict --timestamped`

Notes:
1. CLI generation now writes sidecar metadata (`*.json`) next to each PNG.
2. `inspect` evaluates actual PNG pixels and uses sidecar metadata when present.

Release gate workflow:
1. `python -m experiments.release_quality_gate --styles all --count-per-style 1 --size 128 --quality-profile default --allow-failures 0`
2. Review `textures/review/gates/<timestamp>/gate-report.json` and `contact-sheet.png`.
