# T2 Packaging

Contains the Linux/amd64 submission Dockerfile, pinned runtime dependencies and an unsealed
Development descriptor template. Forecast intelligence remains under `tracks/t2_agenthon/`.

Never upload the template unchanged. Generate the real descriptor with
`scripts/prepare_t2_submission.ps1`, then let official `qfbench2 submission pack` derive/verify
the team identity and seal `descriptor_digest`.
