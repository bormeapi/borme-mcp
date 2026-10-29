"""Starts server.py over stdio and checks its tools/list against tools.json.

Run from the repository root with the dependencies installed:
    python tests/test_tools_list.py [command ...]
With no command it runs `python server.py`; CI also passes a `docker run`
command to test the image. Listing must work with no key and no network.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED = json.loads((ROOT / "tools.json").read_text(encoding="utf-8"))["tools"]


def send(proc, msg):
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()


def read_reply(proc, want_id):
    for line in proc.stdout:
        line = line.strip()
        if line.startswith("{"):
            msg = json.loads(line)
            if msg.get("id") == want_id:
                return msg
    raise AssertionError(f"no reply to request {want_id}")


def main(argv):
    cmd = argv[1:] or [sys.executable, "server.py"]
    proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            text=True, encoding="utf-8")
    try:
        send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "ci", "version": "0"}}})
        read_reply(proc, 1)
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = read_reply(proc, 2)["result"]["tools"]
    finally:
        proc.stdin.close()
        proc.terminate()
        proc.wait(timeout=10)

    assert len(tools) == 10, f"expected 10 tools, got {len(tools)}"
    got = {t["name"]: t for t in tools}
    want = {t["name"]: t for t in EXPECTED}
    assert set(got) == set(want), f"names differ: {sorted(set(got) ^ set(want))}"
    for name, tool in want.items():
        assert got[name]["description"] == tool["description"], f"{name}: description differs"
        assert got[name]["inputSchema"] == tool["inputSchema"], f"{name}: inputSchema differs"
    print(f"tools/list: {len(tools)} tools, names, descriptions and schemas match tools.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
