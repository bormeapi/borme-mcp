"""MCP prompts and resource descriptions, shared with the hosted server.

A prompt is a ready-made instruction a client offers its user (Claude shows
them in the "+" menu, Copilot Studio lists them on the connector): it names
the tools to call, in which order, and the caveats the tool descriptions
already carry, so the answer cites BORME ids and does not overclaim. A prompt
reads no data and calls nothing; the tools it names keep their own plan
checks.

This file is a copy of the hosted server's module, so both servers offer the
same prompts with the same names, arguments and texts: change the hosted copy
first and copy it here. server.py picks the resources the local server can
serve and adjusts their descriptions. The texts are English, like the tool
descriptions, and tell the model to answer in the user's language. Standard
library only.
"""
from __future__ import annotations

import re

# Microsoft 365 Copilot reads at most 1,024 characters of a description; the
# guard tests hold every prompt, argument and resource description to 1000.
MAX_DESCRIPTION = 1000

# The rules every prompt ends with, from the tool descriptions and the
# proofread of 2026-10-29.
COMMON_RULES = """\
Rules for the answer:
- For every fact taken from a returned BORME event, cite its borme_id and \
publication date. Attribute lookups and mappings (company cards, NIF links) \
to the tool and its returned source; never invent a borme_id for a field \
that has none.
- A name match is not identification or ownership: a fuzzy card is a lead, \
and a brand or holder-name hit is a name match, not confirmed ownership.
- A miss, an empty page or hidden_by_plan is not proof that something does \
not exist: it means "not found in this data" or "outside your plan's window".
- When a response carries plan_window, relay its note and its \
date_from_effective; if the period asked for starts earlier, say that the \
earlier period was not searched.
- A plan refusal (for example "needs the basic plan") is part of the answer: \
say what could not be checked and why, relay how to get access, and continue \
only with the steps that do not depend on it.
- Relay tell_the_user, nif_caveat and any source notice a response carries.
- BORME publishes what the Registro Mercantil records; it is not a statement \
of the company's current situation or financial health. Do not give legal, \
credit or investment advice.
- Keep company names, people's names and act texts as published; answer in \
the user's language."""

PAGING = ('keep limit and order, and while next_offset is not null request '
          'the next page with offset set to next_offset')

PROMPTS = {
    "company_due_diligence": {
        "title": "Company due diligence",
        "description": (
            "Due-diligence brief on one Spanish company from the notices "
            "published in BORME: identification, published history, officer "
            "appointments and their later changes, and insolvency and status "
            "notices, each act cited with its BORME id, within your plan's "
            "history window. Uses search_companies or company_by_nif, then "
            "company_history."),
        "arguments": {
            "company": "Company name, slug (e.g. vaz-metales-sl) or NIF/CIF "
                       "(e.g. A28015865).",
        },
    },
    "board_changes": {
        "title": "Board changes",
        "description": (
            "Appointments, re-elections, terminations and resignations, "
            "revocations and ex officio cancellations of appointments of the "
            "directors and other officers of one Spanish company, from the "
            "notices published in BORME, optionally since a date, each change "
            "cited with its BORME id. Uses search_companies, then "
            "company_history."),
        "arguments": {
            "company": "Company name or slug, e.g. \"Mercadona\" or vaz-metales-sl.",
            "since": "Earliest publication date to cover, YYYY-MM-DD, e.g. "
                     "2025-01-01; leave empty for the company's whole history "
                     "within your plan.",
        },
    },
    "new_companies_digest": {
        "title": "New companies digest",
        "description": (
            "Companies whose incorporation notices were published in BORME on "
            "one day, for one Spanish province or autonomous community, with "
            "name, slug and BORME id, from search_events (act type "
            "INCORPORATION). Without a date, uses the latest publication day "
            "(daily_digest)."),
        "arguments": {
            "province": "BORME province or autonomous community, e.g. MADRID, "
                        "VIZCAYA, Catalonia.",
            "date": "Publication day, YYYY-MM-DD, e.g. 2026-10-27; leave empty "
                    "for the latest day in the database.",
        },
    },
    "check_nif": {
        "title": "Check a NIF",
        "description": (
            "Check a Spanish NIF/CIF tax ID against the BORME API's "
            "company-to-NIF links: the company linked to it in this data, any "
            "format or check-character problem the tool reports, and the "
            "linked company's latest published acts. Uses company_by_nif "
            "(Basic plan or higher), then company_history."),
        "arguments": {
            "nif": "NIF/CIF, a letter and 8 characters, e.g. B12345674; spaces, "
                   "hyphens, dots and the ES prefix are accepted.",
        },
    },
}

_NIF_LIKE = re.compile(r"^(ES)?[A-Z][0-9]{7}[0-9A-J]$")
_SLUG_LIKE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)+$")


def _looks_like_nif(value: str) -> bool:
    return bool(_NIF_LIKE.match(re.sub(r"[\s.\-]", "", value).upper()))


def _quoted(value: str) -> str:
    """An argument as it goes into the text: trimmed, on one line, bounded."""
    return " ".join((value or "").split())[:200]


def _identify(company: str) -> str:
    """Step 1 of the company prompts: from the user's input to one slug."""
    if _SLUG_LIKE.match(company):
        return (f'1. Find the company: "{company}" looks like a company slug, so '
                f'call company_history with company "{company}". If that finds no '
                "company, call search_companies with it as the name instead.")
    return (f'1. Find the company: call search_companies with name "{company}". '
            "If several cards could be the company, list them (name, province, "
            "status, slug) and ask which one is meant; do not pick one silently. "
            "A fuzzy match is a lead, not an identification.")


STOP_IF_UNRESOLVED = ("If no single company is identified, report what was found "
                      "and ask the user; do not run the company steps below until "
                      "one company is resolved.")


def company_due_diligence(company: str) -> str:
    company = _quoted(company)
    if _looks_like_nif(company):
        identify = (f'1. Find the company: "{company}" looks like a NIF/CIF, so '
                    "call company_by_nif with it (Basic plan or higher). Interpret "
                    "invalid_input, nif_check_character_failed, not_registry_entity "
                    "and ambiguous answers as the response's note and tell_the_user "
                    "explain them.")
    else:
        identify = _identify(company)
    return f"""\
Prepare a due-diligence brief on the Spanish company "{company}" from the \
notices published in BORME, using the BORME API tools.

{identify} {STOP_IF_UNRESOLVED}
2. History: call company_history with company set to the resolved slug and \
order "desc"; {PAGING}, as far as the brief needs, and say which period was \
read. Note incorporation, name changes, address changes, capital changes, \
mergers, dissolution and extinction, with dates.
3. Officer appointments: list the APPOINTMENTS and RE_ELECTIONS found, with \
any later TERMINATIONS, REVOCATIONS or APPOINTMENT_CANCELLATIONS of the same \
person and role, citing each act. This is a reconstruction from the acts \
read, not a verified list of the current officers: say so, and give the \
period read.
4. Insolvency and status notices: list INSOLVENCY_DECLARATION, \
INSOLVENCY_STATUS, SUSPENSION_OF_PAYMENTS, BANKRUPTCY_LEGACY, DISSOLUTION, \
EXTINCTION, PROVISIONAL_SHEET_CLOSURE_TAX, PROVISIONAL_SHEET_CLOSURE_NIF_REVOKED \
and PROVISIONAL_SHEET_CLOSURE_INSOLVENCY acts. An INSOLVENCY_STATUS notice \
can record any stage of the proceedings: read its payload before saying the \
company was declared insolvent, and do not infer the company's current \
situation from a label alone.
5. Report: one paragraph of summary, then the sections above, then what \
could not be checked (plan window, refusals, pages not read).

{COMMON_RULES}"""


def board_changes(company: str, since: str = "") -> str:
    company, since = _quoted(company), _quoted(since)
    period = (f"published on or after {since}" if since
              else "over the whole history your plan covers")
    stop = (f" Stop once the events are older than {since}." if since else "")
    return f"""\
List the changes to the directors and other officers of the Spanish company \
"{company}" {period}, from the notices published in BORME, using the BORME \
API tools.

{_identify(company)} {STOP_IF_UNRESOLVED}
2. Call company_history with company set to the resolved slug and order \
"desc"; {PAGING}.{stop} If plan_window is present, the plan limited the \
search: relay its note and date_from_effective.
3. Keep the acts APPOINTMENTS, RE_ELECTIONS, TERMINATIONS (removals and \
resignations), REVOCATIONS and APPOINTMENT_CANCELLATIONS. For each change \
give the date, the act type, the person as published, the role and the \
borme_id.
4. End with a summary of the changes in the period read. Do not present it \
as a complete list of the current officers: appointments older than the \
period read are not in it.

{COMMON_RULES}"""


def new_companies_digest(province: str, date: str = "") -> str:
    province, date = _quoted(province), _quoted(date)
    if date:
        day = (f"1. The day is {date}. Call search_events with provinces "
               f'["{province}"], act_types ["INCORPORATION"], date_from and '
               f"date_to both {date}, and limit 200.")
    else:
        day = ("1. Call daily_digest without a date to get the latest publication "
               "day, then call search_events with provinces "
               f'["{province}"], act_types ["INCORPORATION"], date_from and date_to '
               "both that day, and limit 200.")
    return f"""\
List the companies whose incorporation notices were published in BORME for \
{province} (Spain) on one publication day, using the BORME API tools.

{day}
2. If the response returns as many events as the limit, say that the list \
was capped and may be incomplete; search_events has no next page, and a \
narrower company_name_contains filter returns only a subset. If it returns \
none, say that no incorporation notice was found for that province and day \
in this data; do not say that the gazette published none. On the free plan \
only the last 7 days are available: relay plan_window and hidden_by_plan.
3. For each company give its name as published, its slug and the borme_id; \
add the registered office, corporate purpose or share capital only where the \
act's payload prints them.
4. End with the number of events returned and of distinct companies, and the \
publication day; if the limit was reached, label them returned counts, not \
totals.

{COMMON_RULES}"""


def check_nif(nif: str) -> str:
    nif = _quoted(nif)
    return f"""\
Check the Spanish tax ID "{nif}" against the BORME API's company-to-NIF \
links, using the BORME API tools.

1. Call company_by_nif with "{nif}". It needs the Basic plan or higher: on a \
plan refusal, say that this lookup needs a key on Basic or a higher plan, \
relay how to get one, and skip the steps below.
2. Interpret the response as follows:
- invalid_input true: the input is not a well-formed NIF/CIF; explain the \
note, ask for the identifier again, and stop. It is not an unmatched NIF.
- reason nif_check_character_failed: the identifier fails the \
check-character rule; relay tell_the_user, give the expected check \
character, and present did_you_mean entries as candidates for the user to \
verify against their document, not as confirmed corrections.
- reason not_registry_entity: explain the entity_type with the response's \
note and caveat; no company is linked to this identifier in this data.
- ambiguous true: list the candidates and ask which company is meant.
- a hit: name the company, its slug and status; repeat nif_caveat if present \
(the link is then not settled) and relay the source notices.
- found false otherwise: the NIF is not matched to a company yet. That is not \
proof that the company does not exist; NIF links cover a minority of \
companies.
3. Only on a hit that is not ambiguous, call company_history with company \
set to the returned company_slug, order "desc" and limit 20, and summarize \
the latest acts with their dates and borme_id.

{COMMON_RULES}"""


RENDER = {
    "company_due_diligence": company_due_diligence,
    "board_changes": board_changes,
    "new_companies_digest": new_companies_digest,
    "check_nif": check_nif,
}

# Resources: what a client can attach as context without calling a tool.
RESOURCES = {
    "act-types": {
        "uri": "borme://act-types",
        "title": "BORME act types",
        "description": (
            "Every normalized BORME act type: the enum used by the act_types "
            "filters (act_type), its Spanish label (spanish) and its English "
            "label (english). The same list as the list_act_types tool. Open "
            "to everyone."),
    },
    "provinces": {
        "uri": "borme://provinces",
        "title": "BORME provinces and autonomous communities",
        "description": (
            "The 52 province values BORME prints (Ceuta and Melilla among "
            "them), each with the spellings listed for it, plus Spain's "
            "autonomous communities and the autonomous cities, each with the "
            "names it accepts and the province values a filter on it covers. "
            "The same list as GET /v1/provinces. Open to everyone."),
    },
    "coverage": {
        "uri": "borme://coverage",
        "title": "BORME data coverage and freshness",
        "description": (
            "How much BORME data this server holds and how fresh it is: "
            "approximate event and company counts (estimates), the first and "
            "latest publication day held, and the share of gazette text "
            "structured (weighted by events) over the 30 days up to the latest "
            "processed day. The same report as the registry_stats tool. Open "
            "to everyone."),
    },
    "company": {
        "uri": "borme://company/{slug}",
        "title": "BORME company timeline",
        "description": (
            "Up to 20 of the most recent published events of one company, by "
            "slug (e.g. vaz-metales-sl, as returned by search_companies), "
            "with total_events, first_seen and last_seen: the same answer as "
            "company_history with company set to the slug, limit 20 and order "
            "desc, under the same plan rules (without an API key, the last 7 "
            "days only) and counted as one request. For more, call "
            "company_history."),
    },
}

# A company slug as the companies table stores it.
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
