"""What a public MCP server has to keep true about itself.

The server talks to agents, and everything an agent knows about it comes from
the tool list and the docstrings. There is no user to notice that a promise
drifted, so the promises are checked here instead.
"""
import asyncio
import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def tools():
    import server
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


def test_tools_enumerate_without_a_database(tools, monkeypatch):
    """Introspection must work with no BORME_DSN.

    Glama and every client that lists tools before calling one does exactly
    this, and the Dockerfile says so out loud. If a connection were opened at
    import or listing time, the server would look broken to every directory
    that indexes it while being perfectly fine in use.
    """
    monkeypatch.delenv("BORME_DSN", raising=False)
    assert len(tools) >= 7


def test_readme_tool_table_lists_exactly_the_tools_that_exist(tools):
    """The table is the only place a human reads what this server offers.

    It drifted before: the hosted deployment grew tools the README never
    mentioned, so people self-hosting and people reading the page were told
    different things about the same product.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `(\w+)`", readme, re.M))
    assert documented == set(tools), (
        f"only in README: {documented - set(tools)}; "
        f"only in server.py: {set(tools) - documented}")


def test_every_tool_explains_itself(tools):
    for name, t in tools.items():
        assert t.description and len(t.description) > 40, f"{name} has no usable description"


def test_the_row_cap_promised_to_agents_matches_the_default(tools):
    """A cap an agent is told about and a cap it actually gets must agree.

    Production once set the limit to 50 while search_events told the model it
    could ask for 200; the model asked for 200, silently received 50, and had
    no way to know the answer was truncated. For an agent that is worse than
    an error, so the number in the text is pinned to the number in the code.
    """
    import server
    promised = re.search(r"<=\s*(\d+)", tools["search_events"].description)
    assert promised, "search_events no longer states a row cap"
    assert int(promised.group(1)) == server.MAX_LIMIT, (
        f"docstring promises {promised.group(1)}, MAX_LIMIT default is {server.MAX_LIMIT}")


def test_act_type_vocabulary_is_wellformed():
    entries = yaml.safe_load((ROOT / "vocab" / "act_types.yaml").read_text(encoding="utf-8"))
    assert entries, "vocabulary is empty"
    for e in entries:
        assert e.get("en") and e.get("es"), f"incomplete entry: {e}"
        assert e["en"] == e["en"].upper(), f"enum not uppercase: {e['en']}"


def test_act_types_named_in_the_docs_actually_exist(tools):
    """Docstrings name example enums. An agent will send those strings back."""
    vocab = {e["en"] for e in
             yaml.safe_load((ROOT / "vocab" / "act_types.yaml").read_text(encoding="utf-8"))}
    named = set(re.findall(r"\b[A-Z][A-Z_]{4,}\b", tools["search_events"].description))
    unknown = {n for n in named if n not in vocab} - {"BORME", "YYYY", "MADRID", "CADIZ", "JSON"}
    assert not unknown, f"docstring names act types the vocabulary does not have: {unknown}"


def test_glama_metadata_is_valid_json():
    json.loads((ROOT / "glama.json").read_text(encoding="utf-8"))


def test_the_repository_discloses_no_infrastructure_or_secrets():
    """This repo is public. Keep the audit repeatable instead of periodic.

    Private addresses, cluster-internal names and node ports say where the
    service actually runs; tokens say more. None of it belongs in a public
    tree, and a grep is cheaper than remembering to look.
    """
    patterns = re.compile(
        r"192\.168\.\d|10\.\d+\.\d+\.\d+|\.svc\.cluster\.local|NodePort|:30\d{3}"
        r"|apify_api_|pdl_(live|sdbx)|re_[A-Za-z0-9]{16}|ghp_|AKIA"
        r"|BEGIN [A-Z ]*PRIVATE KEY")
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
    offenders = []
    for rel in tracked:
        p = ROOT / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in patterns.finditer(text):
            line = text[:m.start()].count("\n") + 1
            offenders.append(f"{rel}:{line} {m.group()[:24]}")
    assert not offenders, "public repo discloses: " + "; ".join(offenders)


def test_a_real_dsn_is_never_committed():
    """Placeholders are fine; credentials are not."""
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
    bad = []
    for rel in tracked:
        p = ROOT / rel
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for m in re.finditer(r"postgres(?:ql)?://([^\s:@/]+):([^\s@]+)@", text):
            if m.group(2).lower() not in ("pass", "password", "***", "user"):
                bad.append(f"{rel}: {m.group(1)}:***@")
    assert not bad, "credentials in a public repo: " + "; ".join(bad)
