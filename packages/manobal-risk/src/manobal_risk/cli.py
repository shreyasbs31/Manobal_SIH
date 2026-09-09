"""``manobal-ruleset`` — sign, verify and inspect ruleset artefacts.

Exists so that a ruleset change is a reviewable, signable operation with a
recorded diff (SDD §10.5) rather than an edit someone makes on a server.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .errors import ManobalRiskError
from .ruleset import FORCE_VERIFY_KEY_ENV, load_ruleset
from .signing import generate_keypair, sign_artefact, verify_artefact

SIGNING_KEY_ENV = "MANOBAL_RULESET_SIGNING_KEY"


def _write(message: str) -> None:
    sys.stdout.write(message + "\n")


def _cmd_keygen(_: argparse.Namespace) -> int:
    signing_key, verify_key = generate_keypair()
    _write(
        "Development keypair generated. The production signing key is created inside\n"
        "the HSM and never exists in this form (SDD §7.2).\n"
    )
    _write(f"{SIGNING_KEY_ENV}={signing_key}")
    _write(f"{FORCE_VERIFY_KEY_ENV}={verify_key}")
    return 0


def _cmd_sign(args: argparse.Namespace) -> int:
    signing_key = args.signing_key or os.environ.get(SIGNING_KEY_ENV)
    if not signing_key:
        _write(f"error: no signing key. Set {SIGNING_KEY_ENV} or pass --signing-key.")
        return 2
    signature_path = sign_artefact(Path(args.artefact), signing_key)
    _write(f"signed: {signature_path}")
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    verify_key = args.verify_key or os.environ.get(FORCE_VERIFY_KEY_ENV)
    if not verify_key:
        _write(f"error: no verification key. Set {FORCE_VERIFY_KEY_ENV} or pass --verify-key.")
        return 2
    verify_artefact(Path(args.artefact), verify_key)
    _write(f"signature ok: {args.artefact}")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    ruleset = load_ruleset(args.artefact, require_signature=False)
    _write(
        json.dumps(
            {
                "version": ruleset.version,
                "sha256": ruleset.sha256,
                "tier_bounds": {
                    "t1": ruleset.tier_bounds.t1,
                    "t2": ruleset.tier_bounds.t2,
                    "t3": ruleset.tier_bounds.t3,
                },
                "corroboration_min_domains": ruleset.corroboration_min_domains,
                "hysteresis_cycles": ruleset.hysteresis_cycles,
                "coverage_floor": ruleset.coverage_floor,
                "domains": {
                    domain.value: {
                        "weight": spec.weight,
                        "corroboration_threshold": spec.corroboration_threshold,
                        "indicators": ruleset.expected_indicator_count(domain),
                    }
                    for domain, spec in ruleset.domains.items()
                },
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="manobal-ruleset", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    keygen = sub.add_parser("keygen", help="generate a development Ed25519 keypair")
    keygen.set_defaults(func=_cmd_keygen)

    sign = sub.add_parser("sign", help="write a detached signature for an artefact")
    sign.add_argument("artefact")
    sign.add_argument("--signing-key", default=None)
    sign.set_defaults(func=_cmd_sign)

    verify = sub.add_parser("verify", help="verify an artefact's detached signature")
    verify.add_argument("artefact")
    verify.add_argument("--verify-key", default=None)
    verify.set_defaults(func=_cmd_verify)

    show = sub.add_parser("show", help="print a validated summary of an artefact")
    show.add_argument("artefact")
    show.set_defaults(func=_cmd_show)

    args = parser.parse_args(argv)
    try:
        result: int = args.func(args)
    except ManobalRiskError as exc:
        _write(f"error: {exc}")
        return 1
    return result


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
