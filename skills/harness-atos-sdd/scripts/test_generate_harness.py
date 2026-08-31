#!/usr/bin/env python3
"""Smoke tests for the merge-safe Atos SDD harness generator."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().with_name("generate_harness.py")
PROFILE_COUNTS = {"minimal": 10, "standard": 18, "high-risk": 24}


def invoke(root: Path, profile: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(SCRIPT),
            "--project-root",
            str(root),
            "--project-name",
            "Projeto Átomos",
            "--profile",
            profile,
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


class GeneratorTests(unittest.TestCase):
    def test_all_profiles_apply_validate_and_are_idempotent(self) -> None:
        for profile, count in PROFILE_COUNTS.items():
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                applied = invoke(root, profile, "--apply")
                self.assertEqual(applied.returncode, 0, applied.stderr + applied.stdout)
                self.assertIn(f"create={count}", applied.stdout)

                validated = invoke(root, profile, "--validate")
                self.assertEqual(
                    validated.returncode, 0, validated.stderr + validated.stdout
                )
                self.assertIn(f"files={count}", validated.stdout)
                project = (root / ".harness" / "project.yaml").read_text("utf-8")
                if profile == "minimal":
                    self.assertIn("product_requirements: null", project)
                    self.assertIn("specifications: null", project)
                else:
                    self.assertIn("product_requirements: docs/product/PRD.md", project)
                    self.assertIn("specifications: docs/specs", project)

                repeated = invoke(root, profile)
                self.assertEqual(repeated.returncode, 0, repeated.stderr)
                self.assertIn(f"preserve-compatible={count}", repeated.stdout)

    def test_existing_files_are_preserved_and_reported_for_integration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents = root / "AGENTS.md"
            agents.write_text("# Regras locais\n", encoding="utf-8")
            workflow = root / ".github" / "workflows" / "ci.yml"
            workflow.parent.mkdir(parents=True)
            workflow.write_text("name: existente\n", encoding="utf-8")

            planned = invoke(root, "minimal")
            self.assertEqual(planned.returncode, 0, planned.stderr)
            self.assertIn("INTEGRATION-REQUIRED AGENTS.md", planned.stdout)

            applied = invoke(root, "minimal", "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertEqual(agents.read_text(encoding="utf-8"), "# Regras locais\n")
            self.assertEqual(workflow.read_text(encoding="utf-8"), "name: existente\n")

    def test_profile_upgrade_requires_explicit_controlled_file_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(invoke(root, "minimal", "--apply").returncode, 0)

            planned = invoke(root, "standard")
            self.assertEqual(planned.returncode, 0, planned.stderr)
            self.assertIn("CREATE               docs/product/PRD.md", planned.stdout)
            self.assertIn(
                "INTEGRATION-REQUIRED .harness/gates.json", planned.stdout
            )

            self.assertEqual(invoke(root, "standard", "--apply").returncode, 0)
            validation = invoke(root, "standard", "--validate")
            self.assertEqual(validation.returncode, 1)
            self.assertIn("diverge do perfil validado", validation.stdout)

    def test_validate_rejects_invalid_gate_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(invoke(root, "minimal", "--apply").returncode, 0)
            (root / ".harness" / "gates.json").write_text("null\n", encoding="utf-8")

            validation = invoke(root, "minimal", "--validate")
            self.assertEqual(validation.returncode, 1)
            self.assertIn("gates.json deve conter um objeto", validation.stdout)

    def test_runner_uses_unique_evidence_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            applied = invoke(
                root,
                "minimal",
                "--fast-command",
                "python --version",
                "--apply",
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)
            runner = root / ".harness" / "scripts" / "run_gates.py"
            for _ in range(2):
                completed = subprocess.run(
                    [sys.executable, "-X", "utf8", str(runner), "--run"],
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                self.assertEqual(
                    completed.returncode, 0, completed.stderr + completed.stdout
                )
            evidence_root = root / ".harness" / "evidence-local"
            evidence_dirs = [path for path in evidence_root.iterdir() if path.is_dir()]
            self.assertEqual(len(evidence_dirs), 2)
    def test_unicode_and_quoted_commands_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            command = 'python -c "print(\'ação segura\')"'
            applied = invoke(root, "minimal", "--fast-command", command, "--apply")
            self.assertEqual(applied.returncode, 0, applied.stderr)
            gates = json.loads((root / ".harness" / "gates.json").read_text("utf-8"))
            self.assertEqual(gates["groups"]["fast"], [command])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink indisponível")
    def test_symlink_in_controlled_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out:
            root = Path(tmp)
            destination = Path(out) / "outside.md"
            destination.write_text("fora\n", encoding="utf-8")
            try:
                os.symlink(destination, root / "AGENTS.md")
            except OSError as exc:
                self.skipTest(f"ambiente não permite symlink: {exc}")

            result = invoke(root, "minimal", "--apply")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(destination.read_text(encoding="utf-8"), "fora\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
