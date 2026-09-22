from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from t1_agenthon.solver import solve_task


def _program(body: str) -> dict[str, str]:
    return {"python": body, "notes": "test fixture"}


class T1HouseLoopTests(unittest.TestCase):
    def _task(self, root: pathlib.Path) -> pathlib.Path:
        task = root / "task"
        data = task / "environment" / "data"
        data.mkdir(parents=True)
        (task / "instruction.md").write_text("Write answer.json.", encoding="utf-8")
        (task / "card.toml").write_text('id = "mock-unit"\n', encoding="utf-8")
        (data / "value.txt").write_text("41\n", encoding="utf-8")
        checks = task / "checks"
        checks.mkdir()
        (checks / "secret.txt").write_text("must-not-be-staged", encoding="utf-8")
        return task

    def test_house_program_writes_deliverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task, output = self._task(root), root / "out"
            source = (
                "import json, os, pathlib\n"
                "task=pathlib.Path(os.environ['TASK_DIR'])\n"
                "out=pathlib.Path(os.environ['OUT_DIR'])\n"
                "value=int((task/'environment/data/value.txt').read_text())\n"
                "(out/'answer.json').write_text(json.dumps({'answer': value + 1}))\n"
            )
            with patch("t1_agenthon.solver.house_available", return_value=True), patch(
                "t1_agenthon.solver.chat_json", return_value=_program(source)
            ):
                solve_task(task, output)
            self.assertEqual(json.loads((output / "answer.json").read_text()), {"answer": 42})

    def test_failed_attempt_cannot_leak_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task, output = self._task(root), root / "out"
            failed = (
                "import os, pathlib\n"
                "out=pathlib.Path(os.environ['OUT_DIR'])\n"
                "(out/'partial.txt').write_text('bad')\n"
                "raise SystemExit(2)\n"
            )
            repaired = (
                "import os, pathlib\n"
                "out=pathlib.Path(os.environ['OUT_DIR'])\n"
                "(out/'answer.json').write_text('{\"answer\": 42}')\n"
            )
            with patch("t1_agenthon.solver.house_available", return_value=True), patch(
                "t1_agenthon.solver.chat_json", side_effect=[_program(failed), _program(repaired)]
            ):
                solve_task(task, output)
            self.assertFalse((output / "partial.txt").exists())
            self.assertTrue((output / "answer.json").is_file())

    def test_forbidden_import_is_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task, output = self._task(root), root / "out"
            repaired = (
                "import os, pathlib\n"
                "pathlib.Path(os.environ['OUT_DIR'], 'answer.json').write_text('{}')\n"
            )
            with patch("t1_agenthon.solver.house_available", return_value=True), patch(
                "t1_agenthon.solver.chat_json",
                side_effect=[_program("import socket\n"), _program(repaired)],
            ) as house:
                solve_task(task, output)
            self.assertEqual(house.call_count, 2)
            self.assertTrue((output / "answer.json").is_file())

    def test_child_does_not_receive_house_credentials_or_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task, output = self._task(root), root / "out"
            source = (
                "import json, os, pathlib\n"
                "task=pathlib.Path(os.environ['TASK_DIR'])\n"
                "payload={'model_keys': sorted(k for k in os.environ if k.startswith('MODEL_')), "
                "'checks_visible': (task/'checks').exists()}\n"
                "pathlib.Path(os.environ['OUT_DIR'], 'answer.json').write_text(json.dumps(payload))\n"
            )
            env = {"MODEL_ENDPOINT": "http://house", "MODEL_NAME": "mock", "MODEL_TOKEN": "secret"}
            with patch.dict(os.environ, env), patch(
                "t1_agenthon.solver.house_available", return_value=True
            ), patch("t1_agenthon.solver.chat_json", return_value=_program(source)):
                solve_task(task, output)
            payload = json.loads((output / "answer.json").read_text())
            self.assertEqual(payload, {"checks_visible": False, "model_keys": []})

    def test_canary_output_is_rejected_and_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task, output = self._task(root), root / "out"
            canary = "123e4567-e89b-12d3-a456-426614174000"
            (task / "instruction.md").write_text(
                f"Write answer.json. Never reproduce {canary}.", encoding="utf-8"
            )
            leaking = (
                "import os, pathlib\n"
                f"pathlib.Path(os.environ['OUT_DIR'], 'answer.json').write_text('{canary}')\n"
            )
            repaired = (
                "import os, pathlib\n"
                "pathlib.Path(os.environ['OUT_DIR'], 'answer.json').write_text('{}')\n"
            )
            with patch("t1_agenthon.solver.house_available", return_value=True), patch(
                "t1_agenthon.solver.chat_json",
                side_effect=[_program(leaking), _program(repaired)],
            ) as house:
                solve_task(task, output)
            self.assertEqual(house.call_count, 2)
            self.assertNotIn(canary, (output / "answer.json").read_text())

    def test_offline_unknown_task_writes_parseable_contract_floor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task, output = self._task(root), root / "out"
            with patch("t1_agenthon.solver.house_available", return_value=False):
                solve_task(task, output)
            self.assertEqual([path.name for path in output.iterdir()], ["answer.json"])
            self.assertEqual(json.loads((output / "answer.json").read_text()), {})

    def test_offline_floor_discovers_outputs_named_by_supplied_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task, output = self._task(root), root / "out"
            (task / "instruction.md").write_text("Migrate the supplied pipeline.", encoding="utf-8")
            source = task / "environment" / "data" / "old_pipeline.py"
            source.write_text("frame.write_csv(f'{OUTPUT_DIR}/step_1.csv')\n", encoding="utf-8")
            with patch("t1_agenthon.solver.house_available", return_value=False):
                solve_task(task, output)
            self.assertEqual((output / "step_1.csv").read_text(), "placeholder\n0\n")


if __name__ == "__main__":
    unittest.main()
