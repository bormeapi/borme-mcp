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


# Tools the hosted endpoint serves and this server.py does not. The README
# documents the hosted endpoint, so its table lists them too; the self-hosting
# section has to name each one as missing here.
HOSTED_ONLY = {"brand_owner", "company_brands"}


@pytest.mark.parametrize("readme_name", ["README.md", "README.es.md"])
def test_readme_tool_table_lists_exactly_the_tools_that_exist(tools, readme_name):
    """The table is the only place a human reads what this server offers.

    It drifted before: the hosted deployment grew tools the README never
    mentioned, so people self-hosting and people reading the page were told
    different things about the same product. A hosted-only tool is allowed
    only when it is declared above and the self-hosting section says so.
    """
    readme = (ROOT / readme_name).read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `(\w+)`", readme, re.M))
    expected = set(tools) | HOSTED_ONLY
    assert documented == expected, (
        f"only in {readme_name}: {documented - expected}; "
        f"missing from {readme_name}: {expected - documented}")
    assert not HOSTED_ONLY & set(tools), "server.py has it now: drop it from HOSTED_ONLY"
    self_hosting = readme.split("server.py` ", 1)[1].split("\n## ", 1)[0]
    for name in HOSTED_ONLY:
        assert f"`{name}`" in self_hosting, f"{readme_name}: self-hosting section does not name {name}"


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
        # This file spells the patterns out, so it matches every one of them.
        # Skipping it is the only exclusion, and it is a narrow one: a secret
        # would have to be hidden inside the scanner itself to escape.
        if rel == "tests/test_server.py":
            continue
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


def test_list_act_types_matches_borme_core_shape():
    """Same fields and meaning as borme-core's list_act_types and /v1/act-types.

    `spanish` stays (clients read it); `english` was added when borme-core
    started publishing it. Every enum needs an English label: a missing one
    would reach agents as null.
    """
    import server
    rows = json.loads(server.list_act_types())
    vocab = yaml.safe_load((ROOT / "vocab" / "act_types.yaml").read_text(encoding="utf-8"))
    assert [r["act_type"] for r in rows] == sorted({e["en"] for e in vocab})
    for r in rows:
        assert set(r) == {"act_type", "spanish", "english"}, r
        assert r["spanish"] and r["english"], f"incomplete row: {r}"
    by_enum = {r["act_type"]: r for r in rows}
    # `label` overrides `es` where the first `es` names only one stage
    assert by_enum["BANKRUPTCY_LEGACY"]["spanish"] == "Quiebra"
    assert by_enum["INCORPORATION"] == {
        "act_type": "INCORPORATION", "spanish": "Constitución", "english": "Incorporation"}


def test_english_labels_cover_exactly_the_vocabulary():
    labels = yaml.safe_load((ROOT / "vocab" / "labels_en.yaml").read_text(encoding="utf-8"))
    vocab = yaml.safe_load((ROOT / "vocab" / "act_types.yaml").read_text(encoding="utf-8"))
    assert set(labels["act_types"]) == {e["en"] for e in vocab}
