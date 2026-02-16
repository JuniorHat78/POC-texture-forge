import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments import release_quality_gate


def _arg_value(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


def _write_fake_inspect_artifacts(
    inspect_out: pathlib.Path,
    *,
    evaluated: int,
    pass_count: int,
    failed_files: list[str],
) -> None:
    run_dir = inspect_out / "20990101T000000Z"
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "summary": {
            "evaluated": evaluated,
            "pass_count": pass_count,
            "failed_files": failed_files,
        }
    }
    (run_dir / "quality-report.json").write_text(json.dumps(report), encoding="utf-8")
    (run_dir / "contact-sheet.png").write_bytes(b"fake-png")


class ReleaseQualityGateTests(unittest.TestCase):
    def test_run_gate_success_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            config = release_quality_gate.GateConfig(
                out_root=tmp_path / "gates",
                sample_root=tmp_path / "samples",
                styles="moss,lava",
                count_per_style=1,
                size=128,
                seed=222,
                preset="game-ready",
                quality_profile="default",
                allow_failures=0,
                skip_tests=False,
            )

            def fake_cli(argv: list[str]) -> int:
                command = argv[0]
                if command == "matrix":
                    return 0
                if command == "inspect":
                    inspect_out = pathlib.Path(_arg_value(argv, "--out"))
                    _write_fake_inspect_artifacts(
                        inspect_out,
                        evaluated=2,
                        pass_count=2,
                        failed_files=[],
                    )
                    return 0
                self.fail(f"unexpected command: {command}")
                return 1

            with mock.patch("experiments.release_quality_gate._run_unit_tests", return_value=0):
                with mock.patch("experiments.release_quality_gate.texture_cli_main", side_effect=fake_cli):
                    exit_code, report, report_path = release_quality_gate.run_gate(
                        config,
                        repo_root=tmp_path,
                    )

            self.assertEqual(exit_code, 0)
            self.assertTrue(report_path.exists())
            self.assertTrue(report["overall_pass"])
            self.assertEqual(report["failed_count"], 0)
            self.assertEqual(report["config"]["inspect_limit"], 2)
            self.assertEqual(report["steps"]["tests_exit_code"], 0)
            self.assertIsNotNone(report["artifacts"]["quality_report"])
            self.assertIsNotNone(report["artifacts"]["contact_sheet"])

    def test_run_gate_fails_when_failures_exceed_allowance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            config = release_quality_gate.GateConfig(
                out_root=tmp_path / "gates",
                sample_root=tmp_path / "samples",
                styles="all",
                count_per_style=1,
                size=128,
                seed=333,
                preset="game-ready",
                quality_profile="strict",
                allow_failures=1,
                skip_tests=True,
            )

            def fake_cli(argv: list[str]) -> int:
                command = argv[0]
                if command == "matrix":
                    return 0
                if command == "inspect":
                    inspect_out = pathlib.Path(_arg_value(argv, "--out"))
                    _write_fake_inspect_artifacts(
                        inspect_out,
                        evaluated=3,
                        pass_count=1,
                        failed_files=["a.png", "b.png"],
                    )
                    return 0
                self.fail(f"unexpected command: {command}")
                return 1

            with mock.patch("experiments.release_quality_gate.texture_cli_main", side_effect=fake_cli):
                exit_code, report, _report_path = release_quality_gate.run_gate(
                    config,
                    repo_root=tmp_path,
                )

            self.assertEqual(exit_code, 1)
            self.assertFalse(report["overall_pass"])
            self.assertEqual(report["failed_count"], 2)
            self.assertEqual(report["failed_files"], ["a.png", "b.png"])
            self.assertFalse(report["steps"]["tests_ran"])
            self.assertEqual(report["steps"]["tests_exit_code"], 0)

    def test_main_rejects_negative_allow_failures(self) -> None:
        with self.assertRaises(SystemExit):
            release_quality_gate.main(["--allow-failures", "-1"])

    def test_main_resolves_relative_paths_under_repo_root(self) -> None:
        with mock.patch(
            "experiments.release_quality_gate.run_gate",
            return_value=(0, {}, pathlib.Path("x")),
        ) as run_gate_mock:
            code = release_quality_gate.main(
                [
                    "--skip-tests",
                    "--out-root",
                    "tmp/gates",
                    "--sample-root",
                    "tmp/samples",
                ]
            )

        self.assertEqual(code, 0)
        self.assertEqual(run_gate_mock.call_count, 1)
        args, kwargs = run_gate_mock.call_args
        called_config = args[0]
        repo_root = kwargs["repo_root"]
        self.assertEqual(called_config.out_root, repo_root / "tmp/gates")
        self.assertEqual(called_config.sample_root, repo_root / "tmp/samples")


if __name__ == "__main__":
    unittest.main()
