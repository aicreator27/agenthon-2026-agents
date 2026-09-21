from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

import numpy as np
import pandas as pd

from t2_agenthon.cli import main


class T2SubmissionContractTest(unittest.TestCase):
    def test_cli_writes_exact_deterministic_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            unit = pathlib.Path(raw) / "unit"
            panels = unit / "panels"
            text = unit / "text"
            output_a = pathlib.Path(raw) / "out-a"
            output_b = pathlib.Path(raw) / "out-b"
            panels.mkdir(parents=True)
            text.mkdir()
            (text / "note.txt").write_text("2024-06-01: neutral fixture", encoding="utf-8")
            (unit / "card.toml").write_text(
                """
schema_version = "2.0"
[task]
id = "t2-test-joint"
track = "forecasting"
[targets]
asset_ids = ["A", "B"]
horizons = [5, 20]
target_type = "level"
target_frequency = "daily"
""".strip()
                + "\n",
                encoding="utf-8",
            )
            dates = pd.bdate_range("2023-01-02", periods=260)
            rows = []
            for index, date in enumerate(dates):
                common = np.sin(index / 11.0) * 0.01
                rows.extend(
                    [
                        {"date": date, "asset": "A", "value": 4.0 + index * 0.001 + common},
                        {"date": date, "asset": "B", "value": 3.0 + index * 0.0008 + common},
                    ]
                )
            pd.DataFrame(rows).to_parquet(panels / "panel.parquet", index=False)

            arguments = [
                "--panels",
                str(panels),
                "--text",
                str(text),
                "--asof",
                str(dates[-1].date()),
                "--n-draws",
                "200",
                "--seed",
                "7",
            ]
            self.assertEqual(main(arguments + ["--out", str(output_a / "forecast.parquet")]), 0)
            self.assertEqual(main(arguments + ["--out", str(output_b / "forecast.parquet")]), 0)

            expected = {"forecast.parquet", "forecast_meta.json", "forecast_rationale.md"}
            self.assertEqual({path.name for path in output_a.iterdir()}, expected)
            frame_a = pd.read_parquet(output_a / "forecast.parquet")
            frame_b = pd.read_parquet(output_b / "forecast.parquet")
            self.assertEqual(list(frame_a.columns), ["draw", "asset", "horizon", "value"])
            self.assertEqual(len(frame_a), 200 * 2 * 2)
            self.assertTrue(np.isfinite(frame_a["value"]).all())
            pd.testing.assert_frame_equal(frame_a, frame_b)
            metadata = json.loads((output_a / "forecast_meta.json").read_text())
            self.assertEqual(metadata["unit_id"], "t2-test-joint")
            self.assertEqual(metadata["n_draws"], 200)
            self.assertEqual(metadata["asset_ids"], ["A", "B"])
            self.assertEqual(metadata["horizons"], [5, 20])


if __name__ == "__main__":
    unittest.main()

