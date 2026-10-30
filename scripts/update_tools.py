"""Regenerate tools.json from the hosted server's live lists.

Run from the repository root:

    python scripts/update_tools.py          # rewrite tools.json
    python scripts/update_tools.py --check  # exit 1 if tools.json is stale

It asks https://mcp.bormeapi.com/mcp, anonymously, for tools/list,
prompts/list, resources/list and resources/templates/list, and stores the
tools (name, title, description, inputSchema, annotations) together with the
prompts, resources and resource templates. server.py registers exactly the
tools tools.json holds, so rerun this script whenever the hosted server
changes a tool, then commit tools.json. CI runs it with --check.
Uses only the standard library.
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "tools.json"
URL = "https://mcp.bormeapi.com/mcp"
# Cloudflare refuses the default urllib User-Agent.
USER_AGENT = "borme-mcp-tools-sync/1.0 (+https://github.com/bormeapi/borme-mcp)"


def rpc(method):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method}).encode()
    req = urllib.request.Request(URL, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        answer = json.loads(resp.read().decode("utf-8"))
    if "error" in answer:
        raise SystemExit(f"{method}: {answer['error']}")
    return answer["result"]


def live():
    tools = []
    for t in rpc("tools/list")["tools"]:
        tool = {"name": t["name"]}
        if t.get("title"):
            tool["title"] = t["title"]
        tool["description"] = t.get("description", "")
        tool["inputSchema"] = t["inputSchema"]
        if t.get("annotations"):
            tool["annotations"] = t["annotations"]
        tools.append(tool)
    return {
        "source": URL,
        "tools": tools,
        "prompts": rpc("prompts/list").get("prompts", []),
        "resources": rpc("resources/list").get("resources", []),
        "resourceTemplates": rpc("resources/templates/list").get("resourceTemplates", []),
    }


def render(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def main(argv):
    data = live()
    text = render(data)
    if "--check" in argv:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != text:
            print("tools.json differs from the live server: run "
                  "python scripts/update_tools.py and commit tools.json")
            return 1
        print(f"tools.json matches the live server ({len(data['tools'])} tools)")
        return 0
    TARGET.write_text(text, encoding="utf-8")
    print(f"wrote tools.json: {len(data['tools'])} tools, "
          f"{len(data['prompts'])} prompts, {len(data['resources'])} resources, "
          f"{len(data['resourceTemplates'])} resource templates")
    # server.py serves the prompts and resources of prompts.py; a new or
    # renamed one needs its handler there, which this script cannot write.
    sys.path.insert(0, str(ROOT))
    import prompts
    live_names = ({p["name"] for p in data["prompts"]},
                  {r["name"] for r in data["resources"] + data["resourceTemplates"]})
    if live_names != (set(prompts.PROMPTS), set(prompts.RESOURCES)):
        print("the live prompts or resources differ from prompts.py: copy the "
              "hosted module into prompts.py and update server.py and its tests")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
