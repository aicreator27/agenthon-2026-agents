"""Verify an Agenthon submission archive without printing secret material."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import pathlib
import zipfile

from qfbench2_common.contracts.descriptor import SubmissionDescriptor
from qfbench2_common.team_claim import team_claim_proof


EXPECTED_ENTRIES = {"submission.json", "team-claim.json"}
EXPECTED_DESCRIPTOR_KEYS = {
    "schema_version",
    "interface_version",
    "competition_id",
    "team_id",
    "track",
    "phase",
    "category",
    "image",
    "image_access",
    "models",
    "license",
    "descriptor_digest",
}
EXPECTED_CLAIM_KEYS = {
    "schema_version",
    "site_team_id",
    "descriptor_sha256",
    "proof",
}


def verify(
    archive: pathlib.Path,
    key_path: pathlib.Path,
    team_number: int,
    expected_digest: str,
) -> list[str]:
    checks: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        infos = bundle.infolist()
        names = [info.filename for info in infos]
        assert len(names) == len(set(names)), "duplicate archive entries"
        checks.append("unique_entries")
        assert set(names) == EXPECTED_ENTRIES, f"unexpected archive entries: {names}"
        checks.append("exact_entries")
        assert all(not info.is_dir() and info.file_size > 0 for info in infos), "empty archive entry"
        checks.append("nonempty_files")
        descriptor_bytes = bundle.read("submission.json")
        claim_bytes = bundle.read("team-claim.json")
        assert b"team_key" not in descriptor_bytes.lower() + claim_bytes.lower(), "secret field leaked"
        checks.append("no_secret_field")

    descriptor = json.loads(descriptor_bytes)
    claim = json.loads(claim_bytes)
    checks.append("json_parse")
    assert set(descriptor) == EXPECTED_DESCRIPTOR_KEYS, "descriptor must have exactly 12 fields"
    checks.append("descriptor_keyset")
    parsed = SubmissionDescriptor.from_mapping(descriptor)
    checks.append("official_descriptor_parse")
    assert parsed.track == "coding" and parsed.phase == "dev" and parsed.category == "api"
    checks.append("track_phase_category")
    assert parsed.image_digest == expected_digest
    checks.append("immutable_image_digest")
    assert len(parsed.models) == 1 and parsed.models[0].revision == "rl-030326-fp8"
    checks.append("house_model_disclosure")
    assert set(claim) == EXPECTED_CLAIM_KEYS and claim["schema_version"] == "2.0"
    checks.append("claim_schema")
    assert claim["site_team_id"] == team_number
    checks.append("site_team_id")
    descriptor_sha = hashlib.sha256(descriptor_bytes).hexdigest()
    assert hmac.compare_digest(claim["descriptor_sha256"], descriptor_sha)
    checks.append("descriptor_binding")
    team_key = key_path.read_text(encoding="utf-8").strip()
    expected_proof = team_claim_proof(team_number, team_key, descriptor_sha)
    assert hmac.compare_digest(claim["proof"], expected_proof)
    checks.append("team_proof")
    assert parsed.team_id.startswith("team-") and len(parsed.team_id) == 37
    checks.append("derived_team_id_shape")
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=pathlib.Path)
    parser.add_argument("--team-key-file", type=pathlib.Path, required=True)
    parser.add_argument("--team-number", type=int, required=True)
    parser.add_argument("--image-digest", required=True)
    args = parser.parse_args()
    checks = verify(args.archive, args.team_key_file, args.team_number, args.image_digest)
    print(f"PREUPLOAD_OK checks={len(checks)}/{len(checks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
