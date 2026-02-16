from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .texture_cli import main as texture_cli_main
from .texture_pipeline.presets import quality_profile_names, style_names


@dataclass(frozen=True)
class GateConfig:
    out_root: Path
    sample_root: Path
    styles: str
    count_per_style: int
    size: int
    seed: int
    preset: str | None
    quality_profile: str
    allow_failures: int
    skip_tests: bool


def _resolve_rooted_path(repo_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return repo_root / path


def _run_unit_tests(repo_root: Path) -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=str(repo_root),
        check=False,
    )
    return int(proc.returncode)


def _collect_timestamped_report_dir(base_dir: Path, after_utc: datetime) -> Path | None:
    candidates: list[Path] = []
    if not base_dir.exists():
        return None

    for child in base_dir.iterdir():
        if not child.is_dir():
            continue
        report = child / "quality-report.json"
        if not report.exists():
            continue
        modified = datetime.fromtimestamp(report.stat().st_mtime, tz=timezone.utc)
        if modified >= after_utc:
            candidates.append(child)

    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)


def _style_count(styles_arg: str) -> int:
    known = style_names()
    raw = styles_arg.strip().lower()
    if raw == "all":
        return len(known)
    values = [item.strip().lower() for item in raw.split(",") if item.strip()]
    if not values:
        return len(known)
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return len(deduped)


def run_gate(config: GateConfig, *, repo_root: Path) -> tuple[int, dict[str, Any], Path]:
    started_at = datetime.now(timezone.utc)
    gate_stamp = started_at.strftime("%Y%m%dT%H%M%SZ")
    gate_dir = config.out_root / gate_stamp
    sample_dir = config.sample_root / gate_stamp
    review_base = gate_dir / "inspect"
    gate_report_path = gate_dir / "gate-report.json"

    gate_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    tests_rc = 0
    if not config.skip_tests:
        tests_rc = _run_unit_tests(repo_root)

    matrix_args = [
        "matrix",
        "--styles",
        config.styles,
        "--count-per-style",
        str(config.count_per_style),
        "--size",
        str(config.size),
        "--seed",
        str(config.seed),
        "--out",
        str(sample_dir),
    ]
    if config.preset:
        matrix_args.extend(["--preset", config.preset])
    matrix_rc = texture_cli_main(matrix_args)

    inspect_limit = max(1, config.count_per_style * _style_count(config.styles))
    inspect_args = [
        "inspect",
        "--input",
        str(sample_dir),
        "--out",
        str(review_base),
        "--quality-profile",
        config.quality_profile,
        "--timestamped",
        "--limit",
        str(inspect_limit),
        "--columns",
        "3",
    ]
    inspect_started = datetime.now(timezone.utc)
    inspect_rc = texture_cli_main(inspect_args)

    report_dir = _collect_timestamped_report_dir(review_base, inspect_started)
    quality_report_path = report_dir / "quality-report.json" if report_dir else None
    contact_sheet_path = report_dir / "contact-sheet.png" if report_dir else None

    summary: dict[str, Any] = {}
    if quality_report_path and quality_report_path.exists():
        summary = _load_json(quality_report_path).get("summary", {})

    evaluated = int(summary.get("evaluated", 0))
    pass_count = int(summary.get("pass_count", 0))
    failed_count = max(0, evaluated - pass_count)
    failed_files = [str(item) for item in summary.get("failed_files", [])]

    overall_pass = (
        tests_rc == 0
        and matrix_rc == 0
        and inspect_rc == 0
        and failed_count <= config.allow_failures
    )
    exit_code = 0 if overall_pass else 1
    ended_at = datetime.now(timezone.utc)
    duration_seconds = max(0.0, (ended_at - started_at).total_seconds())

    report = {
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_seconds": duration_seconds,
        "gate_id": gate_stamp,
        "config": {
            "styles": config.styles,
            "count_per_style": config.count_per_style,
            "size": config.size,
            "seed": config.seed,
            "preset": config.preset,
            "quality_profile": config.quality_profile,
            "allow_failures": config.allow_failures,
            "skip_tests": config.skip_tests,
            "inspect_limit": inspect_limit,
            "sample_dir": str(sample_dir),
            "review_base": str(review_base),
        },
        "steps": {
            "tests_ran": not config.skip_tests,
            "tests_exit_code": tests_rc,
            "matrix_exit_code": matrix_rc,
            "inspect_exit_code": inspect_rc,
        },
        "quality_summary": summary,
        "failed_count": failed_count,
        "failed_files": failed_files,
        "artifacts": {
            "quality_report": str(quality_report_path) if quality_report_path else None,
            "contact_sheet": str(contact_sheet_path) if contact_sheet_path else None,
        },
        "overall_pass": overall_pass,
        "exit_code": exit_code,
    }
    _write_json(gate_report_path, report)

    print(gate_report_path)
    if quality_report_path:
        print(quality_report_path)
    if contact_sheet_path:
        print(contact_sheet_path)
    if not overall_pass:
        print("error: release quality gate failed", file=sys.stderr)

    return exit_code, report, gate_report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release-quality-gate",
        description="Run tests + texture quality inspection and emit a gate report.",
    )
    parser.add_argument("--out-root", default="textures/review/gates", help="Gate report output root")
    parser.add_argument("--sample-root", default="textures/gate_samples", help="Generated sample root")
    parser.add_argument("--styles", default="all", help="Styles for matrix command")
    parser.add_argument("--count-per-style", type=int, default=1, help="Textures per style")
    parser.add_argument("--size", type=int, default=128, choices=[128, 256, 512], help="Texture size")
    parser.add_argument("--seed", type=int, default=9500, help="Base seed")
    parser.add_argument("--preset", default="game-ready", help="Preset override")
    parser.add_argument(
        "--quality-profile",
        default="strict",
        choices=quality_profile_names(),
        help="Quality profile for inspection",
    )
    parser.add_argument("--allow-failures", type=int, default=0, help="Max failed textures allowed")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running unit tests")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.allow_failures < 0:
        parser.error("--allow-failures must be >= 0")
    if args.count_per_style <= 0:
        parser.error("--count-per-style must be > 0")

    repo_root = Path(__file__).resolve().parents[1]
    config = GateConfig(
        out_root=_resolve_rooted_path(repo_root, str(args.out_root)),
        sample_root=_resolve_rooted_path(repo_root, str(args.sample_root)),
        styles=str(args.styles),
        count_per_style=int(args.count_per_style),
        size=int(args.size),
        seed=int(args.seed),
        preset=(str(args.preset) if args.preset else None),
        quality_profile=str(args.quality_profile),
        allow_failures=int(args.allow_failures),
        skip_tests=bool(args.skip_tests),
    )
    exit_code, _report, _report_path = run_gate(config, repo_root=repo_root)
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
