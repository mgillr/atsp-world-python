"""CLI: enter / discover / mcp (stdio proxy to ATSP_WORLD_URL — no Genesis import)."""
from __future__ import annotations
import argparse, json, os, sys
from . import enter, Session, DEFAULT_URL, __version__, verify_receipt_shape


def _mcp_stdio(base: str) -> None:
    """Thin MCP stdio ↔ HTTP proxy. Same surface as @optitransfer/atsp-world-mcp."""
    import urllib.request

    tools = [
        {"name": "enter", "description": "Enter ATSP World at T0", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "discover", "description": "Search the tool directory",
         "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}}},
        {"name": "tasks", "description": "List catalyst tasks", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "submit", "description": "Propose a task",
         "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
        {"name": "directory_search", "description": "Alias of discover",
         "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}}},
        {"name": "receipt", "description": "Ledger receipt", "inputSchema": {"type": "object", "properties": {}}},
    ]

    from urllib.parse import quote
    state = {"bearer": None}

    def http(method: str, path: str, args: dict | None) -> dict:
        data = None if method == "GET" else json.dumps(args or {}).encode()
        headers = {"content-type": "application/json", "user-agent": f"atsp-world/{__version__}",
                   "x-atsp-client": "atsp-world-python-mcp"}
        if state["bearer"]:
            headers["Authorization"] = f"Bearer {state['bearer']}"
        req = urllib.request.Request(base.rstrip("/") + path, data=data, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def keep(out: dict) -> None:
        agent = ((out or {}).get("identity") or {}).get("agent") or ""
        if ":" in agent and "." in agent:
            state["bearer"] = agent.split(":", 1)[1]

    def call(name: str, args: dict) -> dict:
        q = quote(str(args.get("q", "")))
        paths = {
            "enter": ("POST", "/v1/enter"),
            "discover": ("GET", f"/v1/discover?q={q}"),
            "directory_search": ("GET", f"/v1/discover?q={q}"),
            "tasks": ("GET", "/v1/tasks"),
            "submit": ("POST", "/v1/submit"),
            "receipt": ("GET", "/v1/receipt"),
        }
        method, path = paths.get(name, ("POST", "/v1/enter"))
        if name != "enter" and not state["bearer"]:
            keep(http("POST", "/v1/enter", {}))
        out = http(method, path, args)
        if name == "enter":
            keep(out)
        return out

    for line in sys.stdin:
        if not line.strip():
            continue
        body = json.loads(line)
        method, rid, params = body.get("method"), body.get("id"), body.get("params") or {}
        if method == "initialize":
            out = {"jsonrpc": "2.0", "id": rid, "result": {
                "protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
                "serverInfo": {"name": "atsp-world", "version": __version__},
                "instructions": "Call enter first."}}
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            out = {"jsonrpc": "2.0", "id": rid, "result": {"tools": tools}}
        elif method == "tools/call":
            try:
                result = call(params.get("name"), params.get("arguments") or {})
                out = {"jsonrpc": "2.0", "id": rid, "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}], "isError": False}}
            except Exception as e:
                out = {"jsonrpc": "2.0", "id": rid, "result": {
                    "content": [{"type": "text", "text": str(e)}], "isError": True}}
        elif method == "ping":
            out = {"jsonrpc": "2.0", "id": rid, "result": {}}
        else:
            out = {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}}
        sys.stdout.write(json.dumps(out) + "\n")
        sys.stdout.flush()


def main(argv=None):
    p = argparse.ArgumentParser(prog="atsp-world")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("enter", help="Enter the world (one shot)")
    e.add_argument("--url", default=os.environ.get("ATSP_WORLD_URL", DEFAULT_URL))
    d = sub.add_parser("discover", help="Search the tool directory")
    d.add_argument("q", nargs="?", default="")
    d.add_argument("--url", default=os.environ.get("ATSP_WORLD_URL", DEFAULT_URL))
    m = sub.add_parser("mcp", help="MCP stdio proxy to ATSP_WORLD_URL (no core)")
    m.add_argument("--url", default=os.environ.get("ATSP_WORLD_URL", DEFAULT_URL))
    a = p.parse_args(argv)
    if a.cmd == "enter":
        out = enter(a.url)
        assert verify_receipt_shape(out.get("receipt") or {}) or out.get("ok")
        print(json.dumps(out, indent=2))
        return
    if a.cmd == "discover":
        s = Session(a.url)
        s.enter()
        print(json.dumps(s.discover(a.q), indent=2))
        return
    if a.cmd == "mcp":
        _mcp_stdio(a.url)


if __name__ == "__main__":
    main()
