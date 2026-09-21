from __future__ import annotations

import pathlib
import tempfile
import unittest

import numpy as np
import pandas as pd

from t1_agenthon.solver import solve_task


class Track1ContractTest(unittest.TestCase):
    def test_black_scholes_exemplar_shape_and_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            task = root / "task" / "environment" / "data"
            first = root / "first"
            second = root / "second"
            task.mkdir(parents=True)
            frame = pd.DataFrame(
                {
                    "option_id": ["call", "put"],
                    "S": [100.0, 100.0],
                    "K": [100.0, 100.0],
                    "T": [1.0, 1.0],
                    "r": [0.05, 0.05],
                    "sigma": [0.2, 0.2],
                    "option_type": ["call", "put"],
                }
            )
            frame.to_parquet(task / "options.parquet", index=False)
            solve_task(root / "task", first)
            solve_task(root / "task", second)
            one = pd.read_parquet(first / "results.parquet")
            two = pd.read_parquet(second / "results.parquet")
            self.assertEqual(
                list(one.columns),
                ["option_id", "price", "delta", "gamma", "vega", "theta"],
            )
            pd.testing.assert_frame_equal(one, two)
            self.assertTrue(np.isfinite(one.select_dtypes(include="number")).all().all())
            self.assertAlmostEqual(
                one.loc[0, "price"] - one.loc[1, "price"],
                100 - 100 * np.exp(-0.05),
                places=10,
            )


if __name__ == "__main__":
    unittest.main()
