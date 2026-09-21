# T2 Agenthon Adapter

Runnable v0.1 submission implementing the official `forecast` verb.

- reads the task card and all panel Parquet files at or before `--asof`;
- preserves authored asset and horizon keys;
- emits joint block-bootstrap and shrinkage Student-t scenario paths;
- supports level, log-return and explicit monthly-horizon handling;
- writes exactly the forecast Parquet, metadata sidecar and non-empty rationale;
- remains fully functional when the network and House endpoint are unavailable.

Text adjustments are intentionally disabled until rolling-origin evidence exists.
