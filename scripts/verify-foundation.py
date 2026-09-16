#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

ENGINE = "http://localhost:8000"
WEB = "http://localhost:3000"
ROLES = (
    "personnel",
    "uwo",
    "counsellor",
    "mo",
    "commander",
    "hq",
    "wdec",
    "dpo",
    "hrms_integrator",
    "admin",
    "director",
)


def request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    token: str | None = None,
) -> dict[str, object]:
    headers = {"accept": "application/json"}
    data: bytes | None = None
    if payload is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    request_obj = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request_obj, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {error.code} {body}") from error


def demo_login(role: str, persona_id: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {"role": role}
    if persona_id is not None:
        body["persona_id"] = persona_id
    return request(f"{ENGINE}/api/v1/auth/demo-login", method="POST", payload=body)


def main() -> int:
    selftest = request(f"{ENGINE}/api/v1/system/selftest")
    print(json.dumps(selftest, indent=2, sort_keys=True))
    if selftest.get("healthy") is not True:
        print("selftest is not healthy", file=sys.stderr)
        return 1

    login = demo_login("wdec")
    verify = request(
        f"{ENGINE}/api/v1/gov/audit/verify",
        method="POST",
        token=str(login["access_token"]),
    )
    print(json.dumps(verify, indent=2, sort_keys=True))
    if verify.get("valid") is not True:
        print("audit chain is not valid", file=sys.stderr)
        return 1

    for role in ROLES:
        persona = "arjun" if role == "personnel" else None
        payload = demo_login(role, persona)
        principal = payload["principal"]
        if not isinstance(principal, dict) or principal.get("role") != role:
            print(f"demo login failed for {role}: {payload}", file=sys.stderr)
            return 1
        print(f"demo login ok: {role} -> {principal.get('actor_id')}")

    web = request(f"{WEB}/api/health")
    if web.get("status") != "ok":
        print(f"web health failed: {web}", file=sys.stderr)
        return 1
    print("foundation verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
