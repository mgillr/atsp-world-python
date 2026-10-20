"""atsp-world — thin public client for ATSP World.

Quickstart
----------
    pip install atsp-world
    python -c "import atsp_world; print(atsp_world.enter())"

This package talks HTTP/JSON only. It holds no trust engine, quorum, combine,
forensics, lifespan, tai, collective inference, Genesis runtime or contract
tooling. Those stay private. See docs/OPEN-CORE.md.

Licence of this client tree: proposed Apache-2.0 (Ryan decides; see OPEN-CORE.md).
Until decided, the repo ships BUSL-1.1 as the umbrella; the proposal is explicit.
"""
from __future__ import annotations
import json, os, urllib.error, urllib.request
from typing import Any
from urllib.parse import urlencode

__version__ = "0.1.1"
DEFAULT_URL = os.environ.get("ATSP_WORLD_URL", "https://atsp-world.ledgerguard-global.workers.dev")


class AtspError(Exception):
    def __init__(self, status: int, body: Any):
        self.status, self.body = status, body
        super().__init__(f"ATSP World {status}: {body}")


def _req(method: str, url: str, payload: dict | None = None, headers: dict | None = None) -> dict:
    data = None if method == "GET" else json.dumps(payload or {}).encode()
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"content-type": "application/json", "user-agent": f"atsp-world/{__version__}", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode() or "{}")
        except Exception:
            body = {"error": str(e)}
        raise AtspError(e.code, body)


class Session:
    """Holds the identity returned by enter() and reuses it on later calls."""

    def __init__(self, base: str = DEFAULT_URL, identity: dict | None = None, headers: dict | None = None):
        self.base = base.rstrip("/")
        self.identity = identity or {}
        self.headers = dict(headers or {})
        self._apply_auth()

    def _apply_auth(self) -> None:
        agent = self.identity.get("agent")
        if agent and ":" in agent:
            self.headers["Authorization"] = f"Bearer {agent.split(':', 1)[1]}"

    def enter(self) -> dict:
        out = _req("POST", f"{self.base}/v1/enter", {}, self.headers)
        self.identity = out.get("identity") or self.identity
        self._apply_auth()
        return out

    def discover(self, q: str = "", limit: int = 20) -> dict:
        return _req("GET", f"{self.base}/v1/discover?{urlencode({'q': q, 'limit': limit})}", headers=self.headers)

    def tasks(self) -> dict:
        return _req("GET", f"{self.base}/v1/tasks", headers=self.headers)

    def submit(self, title: str, criteria: list | None = None) -> dict:
        return _req("POST", f"{self.base}/v1/submit", {"title": title, "criteria": criteria}, self.headers)

    def receipt(self) -> dict:
        return _req("GET", f"{self.base}/v1/receipt", headers=self.headers)

    def trust(self) -> dict:
        return _req("GET", f"{self.base}/v1/trust", headers=self.headers)


def enter(url: str | None = None, **headers) -> dict:
    """One-liner on-ramp. Returns {ok, identity, receipt, result}."""
    return Session(url or DEFAULT_URL, headers=headers).enter()


def verify_receipt_shape(receipt: dict) -> bool:
    """Minimal open check: required fields present and hash looks like sha256 hex.

    Full cryptographic chain verification is specified in spec/receipt-verification.md
    and implemented by the optional open verifier package; this client only sanity-checks
    the JSON shape so agents can fail fast without core access.
    """
    if not isinstance(receipt, dict):
        return False
    h = receipt.get("hash")
    if not isinstance(h, str) or len(h) != 64:
        return False
    try:
        int(h, 16)
    except ValueError:
        return False
    return all(k in receipt for k in ("seq", "hash", "t", "id", "type"))
