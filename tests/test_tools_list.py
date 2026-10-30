"""Starts server.py over stdio and checks what it lists.

tools/list must match tools.json; prompts/list, resources/list and
resources/templates/list must offer exactly the prompts, resources and
resource templates the hosted server offers under the same names, within the
Microsoft Copilot naming rules.

Run from the repository root with the dependencies installed:
    python tests/test_tools_list.py [command ...]
With no command it runs `python server.py`; CI also passes a `docker run`
command to test the image. Listing must work with no key and no network.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = {"company_due_diligence": ["company"], "board_changes": ["company", "since"],
           "new_companies_digest": ["province", "date"], "check_nif": ["nif"]}
REQUIRED = {"company", "province", "nif"}
RESOURCES = {"borme://act-types", "borme://provinces", "borme://coverage"}
TEMPLATES = {"borme://company/{slug}"}
# Microsoft Copilot drops a server whose names fall outside this pattern.
NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
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
        send(proc, {"jsonrpc": "2.0", "id": 3, "method": "prompts/list"})
        prompts = read_reply(proc, 3)["result"]["prompts"]
        send(proc, {"jsonrpc": "2.0", "id": 4, "method": "resources/list"})
        resources = read_reply(proc, 4)["result"]["resources"]
        send(proc, {"jsonrpc": "2.0", "id": 5, "method": "resources/templates/list"})
        templates = read_reply(proc, 5)["result"]["resourceTemplates"]
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
        assert got[name].get("title") == tool.get("title"), f"{name}: title differs"
        assert got[name].get("annotations") == tool.get("annotations"), f"{name}: annotations differ"
    print(f"tools/list: {len(tools)} tools, names, titles, descriptions, schemas and "
          "annotations match tools.json")

    assert len(prompts) == 4, f"expected 4 prompts, got {len(prompts)}"
    got = {p["name"]: [a["name"] for a in p.get("arguments") or []] for p in prompts}
    assert got == PROMPTS, f"prompts differ: {got}"
    for p in prompts:
        assert NAME.match(p["name"]) and p.get("description"), p["name"]
        for a in p["arguments"]:
            assert NAME.match(a["name"]) and a.get("description"), f"{p['name']}.{a['name']}"
            assert a.get("required", False) == (a["name"] in REQUIRED), f"{p['name']}.{a['name']}: required"
    text = json.dumps(prompts)
    assert "anyOf" not in text and "null" not in text, "anyOf or null in prompts/list"
    print(f"prompts/list: {len(prompts)} prompts, names and arguments as expected")

    assert len(resources) == 3, f"expected 3 resources, got {len(resources)}"
    uris = {r["uri"] for r in resources}
    assert uris == RESOURCES, f"resources differ: {sorted(uris)}"
    for r in resources:
        assert NAME.match(r["name"]) and r.get("description"), r["uri"]
    print(f"resources/list: {len(resources)} resources, URIs as expected")

    uris = {t["uriTemplate"] for t in templates}
    assert uris == TEMPLATES, f"resource templates differ: {sorted(uris)}"
    for t in templates:
        assert NAME.match(t["name"]) and t.get("description"), t["uriTemplate"]
    print(f"resources/templates/list: {len(templates)} template, URI as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
