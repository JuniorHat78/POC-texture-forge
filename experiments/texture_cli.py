from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Iterable

from .texture_pipeline.contract import TextureParams
from .texture_pipeline.core import TextureImage, generate_texture
from .texture_pipeline.io import read_json, read_png, write_json, write_png
from .texture_pipeline.presets import (
    defaults,
    get_quality_profile,
    preset_names,
    quality_profile_names,
    style_names,
)
from .texture_pipeline.quality import QualityThresholds, contact_sheet, evaluate_quality


def _add_common_options(parser: argparse.ArgumentParser, *, include_seed: bool = True) -> None:
    parser.add_argument("--style", choices=style_names(), help="Texture style")
    parser.add_argument("--size", type=int, choices=[128, 256, 512], help="Texture size")
    parser.add_argument("--scale", type=int, help="Cell scale (2..32)")
    parser.add_argument("--octaves", type=int, help="Detail layers (1..8)")
    parser.add_argument("--roughness", type=float, help="Roughness (0.0..1.5)")
    parser.add_argument("--contrast", type=float, help="Contrast (0.4..3.0)")
    parser.add_argument("--grain", type=float, help="Grain amount (0.0..0.6)")
    parser.add_argument("--handcraft", type=float, help="Handcrafted layer strength (0.0..1.0)")
    parser.add_argument(
        "--preset",
        choices=preset_names(),
        help="Named preset from texture-presets.json",
    )
    if include_seed:
        parser.add_argument("--seed", type=int, help="Generation seed")


def _build_params(
    args: argparse.Namespace,
    *,
    seed_override: int | None = None,
    style_override: str | None = None,
) -> TextureParams:
    override_seed = seed_override if seed_override is not None else args.seed
    if override_seed is None:
        override_seed = defaults()["seed"]

    overrides = {
        "style": style_override if style_override is not None else args.style,
        "seed": override_seed,
        "size": args.size,
        "scale": args.scale,
        "octaves": args.octaves,
        "roughness": args.roughness,
        "contrast": args.contrast,
        "grain": args.grain,
        "handcraft": args.handcraft,
    }
    return TextureParams.from_overrides(overrides, preset_name=args.preset)


def _render_one(params: TextureParams, out_dir: Path, *, name_override: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = name_override or params.to_filename_stem()
    path = out_dir / f"{stem}.png"
    image = generate_texture(params)
    write_png(path, image)
    write_json(
        path.with_suffix(".json"),
        {
            "params": params.as_dict(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "texture-cli",
        },
    )
    return path


def _command_render(args: argparse.Namespace) -> int:
    try:
        params = _build_params(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    target_out = Path(args.out)
    stem = args.name or params.to_filename_stem()
    path = target_out / f"{stem}.png"
    if args.dry_run:
        print(path)
        return 0

    path = _render_one(params, target_out, name_override=args.name)
    print(path)
    return 0


def _resolve_style_list(styles_arg: str) -> list[str]:
    available = style_names()
    if styles_arg.strip().lower() == "all":
        return available

    requested = [style.strip().lower() for style in styles_arg.split(",") if style.strip()]
    if not requested:
        raise ValueError("styles list cannot be empty")

    unknown = [style for style in requested if style not in available]
    if unknown:
        raise ValueError(f"Unknown style(s): {', '.join(unknown)}")

    deduped: list[str] = []
    for style in requested:
        if style not in deduped:
            deduped.append(style)
    return deduped


def _command_batch(args: argparse.Namespace) -> int:
    if args.count <= 0:
        print("error: --count must be > 0", file=sys.stderr)
        return 2

    base_seed = args.seed if args.seed is not None else random.randint(1_000_000, 999_999_999)
    out_dir = Path(args.out)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    for index in range(args.count):
        try:
            params = _build_params(args, seed_override=base_seed + index)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        if args.dry_run:
            path = out_dir / f"{params.to_filename_stem()}.png"
        else:
            path = _render_one(params, out_dir)
        created.append(path)

    for path in created:
        print(path)
    return 0


def _command_matrix(args: argparse.Namespace) -> int:
    if args.count_per_style <= 0:
        print("error: --count-per-style must be > 0", file=sys.stderr)
        return 2

    try:
        styles = _resolve_style_list(args.styles)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    base_seed = args.seed if args.seed is not None else random.randint(1_000_000, 999_999_999)
    out_dir = Path(args.out)
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    for style_index, style in enumerate(styles):
        for offset in range(args.count_per_style):
            seed = base_seed + style_index * 100_000 + offset
            try:
                params = _build_params(args, seed_override=seed, style_override=style)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2

            if args.dry_run:
                path = out_dir / f"{params.to_filename_stem()}.png"
            else:
                path = _render_one(params, out_dir)
            created.append(path)

    for path in created:
        print(path)
    return 0


def _inspect_textures(
    input_dir: Path,
    *,
    thresholds: QualityThresholds,
) -> tuple[list[dict[str, object]], list[TextureImage], int, list[str]]:
    results: list[dict[str, object]] = []
    images: list[TextureImage] = []
    skipped = 0
    skipped_files: list[str] = []

    def _params_for_file(png_path: Path) -> dict[str, object]:
        sidecar_path = png_path.with_suffix(".json")
        if sidecar_path.exists():
            try:
                sidecar_data = read_json(sidecar_path)
            except (OSError, ValueError):
                sidecar_data = None
            if isinstance(sidecar_data, dict):
                candidate = sidecar_data.get("params", sidecar_data)
                if isinstance(candidate, dict):
                    try:
                        return TextureParams.from_overrides(candidate).as_dict()
                    except ValueError:
                        pass

        try:
            return TextureParams.from_filename_stem(png_path.stem).as_dict()
        except ValueError:
            return {"style": "unknown"}

    for png_path in sorted(input_dir.glob("*.png")):
        try:
            image = read_png(png_path)
        except (OSError, ValueError):
            skipped += 1
            skipped_files.append(png_path.name)
            continue

        params_dict = _params_for_file(png_path)
        metrics = evaluate_quality(image, thresholds=thresholds)
        results.append(
            {
                "file": png_path.name,
                "params": params_dict,
                "metrics": metrics,
            }
        )
        images.append(image)

    return results, images, skipped, skipped_files


def _summarize_metrics(rows: Iterable[dict[str, object]]) -> dict[str, float | int | dict[str, object] | list[str]]:
    rows_list = list(rows)
    if not rows_list:
        return {
            "evaluated": 0,
            "pass_count": 0,
            "avg_seam_score": 0.0,
            "avg_luminance_spread": 0.0,
            "avg_luminance_std": 0.0,
            "failed_files": [],
            "style_breakdown": {},
        }

    seam_scores = [float(row["metrics"]["seam_score"]) for row in rows_list]  # type: ignore[index]
    spreads = [float(row["metrics"]["luminance_spread"]) for row in rows_list]  # type: ignore[index]
    std_values = [float(row["metrics"]["luminance_std"]) for row in rows_list]  # type: ignore[index]
    pass_count = sum(1 for row in rows_list if bool(row["metrics"]["pass_overall"]))  # type: ignore[index]
    failed_files = [
        str(row["file"])
        for row in rows_list
        if not bool(row["metrics"]["pass_overall"])  # type: ignore[index]
    ]

    style_map: dict[str, list[dict[str, object]]] = {}
    for row in rows_list:
        params = row.get("params", {})
        style = "unknown"
        if isinstance(params, dict):
            style = str(params.get("style", "unknown"))
        style_map.setdefault(style, []).append(row)

    style_breakdown: dict[str, object] = {}
    for style, style_rows in style_map.items():
        style_pass = sum(1 for row in style_rows if bool(row["metrics"]["pass_overall"]))  # type: ignore[index]
        style_seams = [float(row["metrics"]["seam_score"]) for row in style_rows]  # type: ignore[index]
        style_spreads = [float(row["metrics"]["luminance_spread"]) for row in style_rows]  # type: ignore[index]
        style_breakdown[style] = {
            "evaluated": len(style_rows),
            "pass_count": style_pass,
            "avg_seam_score": mean(style_seams),
            "avg_luminance_spread": mean(style_spreads),
        }

    return {
        "evaluated": len(rows_list),
        "pass_count": pass_count,
        "avg_seam_score": mean(seam_scores),
        "avg_luminance_spread": mean(spreads),
        "avg_luminance_std": mean(std_values),
        "failed_files": failed_files,
        "style_breakdown": style_breakdown,
    }


def _command_inspect(args: argparse.Namespace) -> int:
    input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"error: input directory does not exist: {input_dir}", file=sys.stderr)
        return 2
    if args.limit <= 0:
        print("error: --limit must be > 0", file=sys.stderr)
        return 2
    if args.columns <= 0:
        print("error: --columns must be > 0", file=sys.stderr)
        return 2

    try:
        thresholds = QualityThresholds.from_mapping(get_quality_profile(args.quality_profile))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    rows, images, skipped, skipped_files = _inspect_textures(input_dir, thresholds=thresholds)
    if not rows:
        print("error: no decodable PNG texture files found for inspection", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    if args.timestamped:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = out_dir / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = _summarize_metrics(rows)
    summary["skipped"] = skipped
    summary["skipped_files"] = skipped_files
    summary["generated_at"] = datetime.now(timezone.utc).isoformat()
    summary["input_dir"] = str(input_dir.resolve())
    summary["quality_profile"] = args.quality_profile
    summary["quality_thresholds"] = thresholds.as_dict()

    report = {
        "summary": summary,
        "textures": rows,
    }

    report_path = out_dir / "quality-report.json"
    write_json(report_path, report)

    sheet = contact_sheet(images[: args.limit], columns=args.columns, padding=2)
    sheet_path = out_dir / "contact-sheet.png"
    write_png(sheet_path, sheet)

    print(report_path)
    print(sheet_path)
    if args.strict and int(summary["pass_count"]) < int(summary["evaluated"]):
        print(
            "error: strict inspection failed because not all textures passed quality thresholds",
            file=sys.stderr,
        )
        return 3

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="texture-cli",
        description="Generate and inspect procedural game textures.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render", help="Render a single texture")
    _add_common_options(render_parser, include_seed=True)
    render_parser.add_argument("--name", help="Optional output filename stem override")
    render_parser.add_argument("--out", default="textures", help="Output directory")
    render_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended output path without writing files",
    )
    render_parser.set_defaults(handler=_command_render)

    batch_parser = subparsers.add_parser("batch", help="Render many textures")
    _add_common_options(batch_parser, include_seed=True)
    batch_parser.add_argument("--count", type=int, default=8, help="Number of textures")
    batch_parser.add_argument("--out", default="textures", help="Output directory")
    batch_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended output paths without writing files",
    )
    batch_parser.set_defaults(handler=_command_batch)

    matrix_parser = subparsers.add_parser(
        "matrix",
        help="Render a style matrix (multiple styles x count-per-style)",
    )
    _add_common_options(matrix_parser, include_seed=True)
    matrix_parser.add_argument(
        "--styles",
        default="all",
        help="Comma-separated style names or 'all' (default: all)",
    )
    matrix_parser.add_argument(
        "--count-per-style",
        type=int,
        default=4,
        help="Number of textures to render for each style",
    )
    matrix_parser.add_argument("--out", default="textures", help="Output directory")
    matrix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended output paths without writing files",
    )
    matrix_parser.set_defaults(handler=_command_matrix)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Evaluate generated textures and build review artifacts",
    )
    inspect_parser.add_argument("--input", default="textures", help="Input directory")
    inspect_parser.add_argument("--out", default="textures/review", help="Report directory")
    inspect_parser.add_argument("--limit", type=int, default=16, help="Max textures for contact sheet")
    inspect_parser.add_argument("--columns", type=int, default=4, help="Contact sheet columns")
    inspect_parser.add_argument(
        "--quality-profile",
        default="default",
        choices=quality_profile_names(),
        help="Quality threshold profile from texture-presets.json",
    )
    inspect_parser.add_argument(
        "--timestamped",
        action="store_true",
        help="Write report artifacts into a UTC timestamped subdirectory",
    )
    inspect_parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero exit code when any texture fails quality thresholds",
    )
    inspect_parser.set_defaults(handler=_command_inspect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 2
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
