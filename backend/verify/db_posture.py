"""Database posture: every table in public, enumerated from pg_class and
classified into exactly one bucket. Not a policy query.

WHY THIS EXISTS
---------------
2026-09-15: a pg_policies query found fourteen tables with a policy named
"Service role full access" written FOR ALL TO public USING (true). The same
query could never have found provider_appeal_letters -- eight appeal letters
with patient names, RLS enabled, NO policy, anon holding full DML -- because
a table with no policy appears in no policy listing. Default-deny kept it
closed; one ALTER TABLE ... DISABLE ROW LEVEL SECURITY would have opened it,
and the instrument would have said nothing. So the subject of the check is
the TABLE, and every table lands in one of these buckets or the test fails:

    service_role_only   RLS on; no policy admits anon/authenticated;
                        anon/authenticated hold no grant
    public_read         allow-listed with a reason (data/verify/db_posture_allow.json);
                        RLS on; the only admitting policy is SELECT USING (true);
                        anon/authenticated hold SELECT only
    user_scoped         every admitting policy's condition references auth.uid();
                        anon/authenticated hold at most the DML those policies need
    gated_read          SELECT admitted only while the row's topic is published
                        (migration 078's `status = 'published'` gate; Signal corpus)
    FAIL                anything else, with the reason(s) named

The name-versus-qual lint is part of it: a policy whose NAME claims a
condition (token / own / user / member / self / service role) while its
qual is `true` is asserting a control it does not implement. Three of three
on 2026-09-15 ("Service role full access" x14, "public read by share token",
018's original) -- a class, not a coincidence.

TRUNCATE is not subject to row-level security. A role holding TRUNCATE on a
table can empty it whatever the policies say; anon and authenticated hold it
by default on every table CREATE TABLE made. No REST verb reaches TRUNCATE,
so nothing exploits it through PostgREST today; it is still a grant with no
legitimate holder and the classifier fails it.

HOW IT RUNS
-----------
The enumeration is a SECURITY DEFINER function in the database,
public.db_posture() (migration 087), EXECUTE granted to service_role only.
tests/verify/test_db_posture.py calls it over RPC with the service key -- the
same credentials the golden-set CI job already holds -- and asserts zero FAIL.
The classifier below is pure Python over the function's JSON so it can also
run offline against a captured fixture (the pre-087 snapshot is the known-bad).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

ALLOW_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "verify", "db_posture_allow.json")

NON_SERVICE = {"public", "anon", "authenticated"}
DML = {"SELECT", "INSERT", "UPDATE", "DELETE"}
NEVER_FOR_CLIENTS = {"TRUNCATE", "REFERENCES", "TRIGGER"}

_SERVICE_ROLE_TEST = re.compile(r"^\(?\s*auth\.role\(\)\s*=\s*'service_role'(?:::text)?\s*\)?$")
_TRUE = re.compile(r"^\(?\s*true\s*\)?$", re.I)
_NAME_CLAIMS_CONDITION = re.compile(r"token|\bown\b|\buser|member|\bself\b|service[ _]?role", re.I)
# The migration-078 gate: a row is readable only while its topic is published.
_PUBLISHED_GATE = re.compile(r"status\s*=\s*'published'")

# The SQL body of public.db_posture(): one JSON object per table in public.
POSTURE_SQL = """
select coalesce(jsonb_agg(row_to_json(t)::jsonb order by t.table_name), '[]'::jsonb) from (
  select c.relname as table_name, c.relrowsecurity as rls_enabled, c.relforcerowsecurity as rls_forced,
    coalesce((select jsonb_agg(jsonb_build_object('name', p.policyname, 'cmd', p.cmd, 'permissive', p.permissive,
                                                  'roles', p.roles, 'qual', p.qual, 'with_check', p.with_check)
                               order by p.policyname)
              from pg_policies p where p.schemaname = 'public' and p.tablename = c.relname), '[]'::jsonb) as policies,
    coalesce((select jsonb_object_agg(g.grantee, g.privs)
              from (select grantee, jsonb_agg(privilege_type order by privilege_type) as privs
                    from information_schema.role_table_grants x
                    where x.table_schema = 'public' and x.table_name = c.relname
                      and grantee in ('anon', 'authenticated', 'service_role', 'PUBLIC')
                    group by grantee) g), '{}'::jsonb) as grants
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind in ('r', 'p')
) t
"""


@dataclass
class Verdict:
    table: str
    bucket: str                       # service_role_only | public_read | user_scoped | FAIL
    reasons: list[str] = field(default_factory=list)
    admitted: list[str] = field(default_factory=list)   # policy names that admit non-service callers


def _allow() -> dict:
    if not os.path.exists(ALLOW_PATH):
        return {}
    return {e["table"]: e["reason"] for e in json.load(open(ALLOW_PATH, encoding="utf-8"))["public_read"]}


def _roles(p: dict) -> set[str]:
    r = p.get("roles") or []
    if isinstance(r, str):
        r = [x.strip() for x in r.strip("{}").split(",") if x.strip()]
    return set(r)


def _condition(p: dict) -> str:
    """The expression a caller must satisfy: qual for reads/updates/deletes,
    with_check for inserts, the stricter of the two for ALL."""
    cmd = (p.get("cmd") or "").upper()
    q, w = p.get("qual"), p.get("with_check")
    if cmd == "INSERT":
        return w or ""
    if cmd == "ALL":
        parts = [x for x in (q, w) if x]
        parts = list(dict.fromkeys(parts))          # USING and WITH CHECK are usually identical
        return " AND ".join(parts) if parts else ""
    return q or ""


def _needs(cmd: str) -> set[str]:
    cmd = cmd.upper()
    return DML if cmd == "ALL" else {cmd}


def classify_table(row: dict, allow: dict) -> Verdict:
    name = row["table_name"]
    v = Verdict(name, "service_role_only")
    grants = row.get("grants") or {}
    client_grants = set(grants.get("anon") or []) | set(grants.get("authenticated") or []) | set(grants.get("PUBLIC") or [])

    if not row.get("rls_enabled"):
        v.reasons.append("rls_disabled")

    needed: set[str] = set()
    public_read_ok = False
    user_scoped = False
    gated_read = False
    for p in row.get("policies") or []:
        if not (_roles(p) & NON_SERVICE):
            continue                                    # TO service_role (or another role): not a client path
        cond = _condition(p)
        pname = p.get("name") or ""
        cmd = (p.get("cmd") or "").upper()
        if _SERVICE_ROLE_TEST.match(cond.strip()):
            continue                                    # written TO public but only service_role can satisfy it
        if not cond.strip() or _TRUE.match(cond.strip()):
            if _NAME_CLAIMS_CONDITION.search(pname):
                v.reasons.append(f"name_claims_condition_qual_is_true: {pname!r}")
            if cmd == "SELECT" and name in allow:
                public_read_ok = True; v.admitted.append(pname); needed |= {"SELECT"}
            else:
                v.reasons.append(f"unconditional_{cmd.lower()}_for_clients: {pname!r}")
            continue
        if "auth.uid()" in cond:
            user_scoped = True; v.admitted.append(pname); needed |= _needs(cmd)
            if _TRUE.match((p.get("with_check") or "x").strip()) and cmd in ("ALL", "UPDATE"):
                v.reasons.append(f"with_check_true_on_{cmd.lower()}: {pname!r}")
            continue
        if cmd == "SELECT" and _PUBLISHED_GATE.search(cond):
            gated_read = True; v.admitted.append(pname); needed |= {"SELECT"}
            continue
        v.reasons.append(f"unrecognised_condition: {pname!r} -> {cond[:80]!r}")

    if user_scoped and public_read_ok:
        v.reasons.append("mixed_user_scoped_and_public_read")

    dormant = client_grants - needed
    if dormant & NEVER_FOR_CLIENTS:
        v.reasons.append("clients_hold_" + "/".join(sorted(dormant & NEVER_FOR_CLIENTS)))
    if (dormant & DML):
        v.reasons.append("dormant_client_grants: " + "/".join(sorted(dormant & DML)))

    if v.reasons:
        v.bucket = "FAIL"
    elif public_read_ok:
        v.bucket = "public_read"
    elif user_scoped:
        v.bucket = "user_scoped"
    elif gated_read:
        v.bucket = "gated_read"
    else:
        v.bucket = "service_role_only"
    return v


def classify(rows: list[dict], allow: dict | None = None) -> list[Verdict]:
    allow = _allow() if allow is None else allow
    out = [classify_table(r, allow) for r in rows]
    # an allow-list entry for a table that no longer exists, or that is not
    # public_read, is dead weight or a lie
    names = {r["table_name"] for r in rows}
    for t in allow:
        if t not in names:
            out.append(Verdict(t, "FAIL", ["allow_list_names_missing_table"]))
    return out


def report(verdicts: list[Verdict]) -> str:
    lines = []
    for b in ("FAIL", "public_read", "gated_read", "user_scoped", "service_role_only"):
        vs = [v for v in verdicts if v.bucket == b]
        lines.append(f"{b}: {len(vs)}")
        if b == "FAIL":
            for v in vs:
                lines.append(f"  {v.table}: " + "; ".join(v.reasons))
    return "\n".join(lines)


def fetch_live() -> list[dict]:
    """Call public.db_posture() with the service key. Raises if credentials are
    absent or the function does not exist (migration 087 not applied)."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from supabase_client import supabase   # noqa: E402  (SUPABASE_URL / SUPABASE_SERVICE_KEY)
    if supabase is None:
        raise RuntimeError("SUPABASE_SERVICE_KEY absent: cannot read the live posture")
    res = supabase.rpc("db_posture", {}).execute()
    return res.data or []


if __name__ == "__main__":
    vs = classify(fetch_live())
    print(report(vs))
    raise SystemExit(1 if any(v.bucket == "FAIL" for v in vs) else 0)


def hygiene_statements(rows: list[dict], allow: dict | None = None,
                       drop_policies: dict[str, list[str]] | None = None) -> list[str]:
    """The REVOKEs that would bring every table to its bucket's grant floor,
    computed from the same rules classify() applies. `drop_policies` names
    policies a migration is about to drop, so the grants they needed are
    treated as no longer needed. Emitted as explicit SQL so a reviewer sees
    exactly which grant leaves which table."""
    allow = _allow() if allow is None else allow
    drop_policies = drop_policies or {}
    out = []
    for r in sorted(rows, key=lambda x: x["table_name"]):
        name = r["table_name"]
        rr = dict(r)
        rr["policies"] = [p for p in (r.get("policies") or []) if p.get("name") not in drop_policies.get(name, [])]
        v = classify_table(rr, allow)
        needed: set[str] = set()
        for p in rr["policies"]:
            if p.get("name") in v.admitted:
                needed |= _needs(p.get("cmd") or "")
        grants = rr.get("grants") or {}
        for role in ("anon", "authenticated"):
            held = set(grants.get(role) or [])
            drop = sorted((held - needed) & (DML | NEVER_FOR_CLIENTS))
            if drop:
                out.append(f"REVOKE {', '.join(drop)} ON public.{name} FROM {role};")
    return out
