"""Promote public domain candidates using purpose-specific evidence and source lineage."""
from collections import defaultdict

from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid, read_rules
from loon_rules.sources.inputs import extract_rows


DOMAIN_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-WILDCARD"}


def blocked_scope(row, shared, reserved, shared_hosts, *, preceding=()):
    kind, host = row.split(",")
    tail = domain_scope.fixed_tail(host)
    try:
        domain_scope.public_host(tail)
    except Invalid:
        return True
    suffix, private = domain_scope.current().suffix(tail)
    if host in shared_hosts:
        return True
    if kind != "DOMAIN" and (tail in shared or tail == suffix):
        return True
    if kind == "DOMAIN" and private and host == suffix:
        return True
    return any(
        domain_scope.covers(other, row) or (domain_scope.covers(row, other) and other not in preceding)
        for other in reserved
    )


def domains(spec, last, downloaded, *, shared=(), reserved=(), shared_hosts=(), excluded=(),recipe_shared_hosts=None,reserved_owners=(),preceding=()):
    facts = defaultdict(list)
    missing = 0
    for source in spec["inputs"]:
        if source["source"] not in downloaded:
            missing += 1
            continue
        text = downloaded[source["source"]]
        rows = extract_rows(source["recipe"], text,
            shared_hosts=shared_hosts if recipe_shared_hosts is None else recipe_shared_hosts) if source.get("recipe") else read_rules(text)
        for row in rows:
            kind, host, *flags = row.split(",")
            if flags or kind not in DOMAIN_TYPES:
                continue
            facts[kind + "," + host.casefold()].append(source)

    policy_excluded = {row for row in facts if any(
        domain_scope.covers(denied,row) or domain_scope.covers(row,denied) for denied in excluded)}
    facts = {row: sources for row, sources in facts.items() if row not in policy_excluded}
    preceding=frozenset(preceding)
    blocked = {row for row,sources in facts.items() if blocked_scope(row, shared, reserved, shared_hosts,
               preceding=preceding if any(source.get('authority') for source in sources) else ())}
    qualified = {row: sources for row, sources in facts.items() if row not in blocked}
    accepted = []
    proofs = {}
    conflicts = unconfirmed = 0
    assigned = defaultdict(int)
    for row in sorted(facts):
        known = any(domain_scope.covers(old, row) for old in last)
        if row in blocked:
            if not known:
                conflicts += 1
                unconfirmed += 1
                owner=next((owner for owner,scope in reserved_owners
                            if row.startswith('DOMAIN,') and domain_scope.covers(scope,row)),None)
                if owner is not None:assigned[owner]+=1
            continue
        support = [
            source for evidence, sources in qualified.items()
            if domain_scope.covers(evidence, row)
            for source in sources
        ]
        families = {source["family"] for source in support}
        official = any(source.get("authority") for source in support)
        if official or len(families) >= spec.get("minimum-families", 2):
            proofs[row] = {
                "families": sorted(families),
                "sources": sorted({source["source"] for source in support}),
                "authority": official,
            }
            if not known:
                accepted.append(row)
        elif not known:
            unconfirmed += 1
    report = {
        "admitted": len(accepted), "unconfirmed": unconfirmed,
        "pending": unconfirmed - conflicts, "scope-conflicts": conflicts,
        "inputs-missing": missing, "proofs": proofs, "policy-excluded": len(policy_excluded),
    }
    if assigned:report['reserved-owners']=dict(assigned)
    return accepted,report


def propose(entries, data, downloaded, *, active, shared, shared_hosts=(),
            protected_sections=("apple", "ai")):
    active=list(active)
    positions={key:index for index,key in enumerate(active)}
    proposals = {}
    report = {}
    for key, entry in entries.items():
        spec = entry.get("discovery")
        if not spec:
            continue
        reservations = [
            (other,row) for other in active if other != key and not entries[other].get("fallback")
            and entries[other].get("policy-hint") != "reject"
            for row in data[other]
            if row.split(",")[0] in DOMAIN_TYPES and row.count(",") == 1
        ]
        try:
            proposals[key], report[key] = domains(
                spec, data[key], downloaded, shared=shared, reserved=[row for _,row in reservations],
                reserved_owners=reservations,
                preceding={row for owner,row in reservations if key in positions and positions[owner]<positions[key]},
                shared_hosts=shared_hosts if entry.get("section") in protected_sections else (),
                recipe_shared_hosts=shared_hosts,
                excluded=entry.get('excluded-rules',()),
            )
        except (Invalid, ValueError, SyntaxError):
            proposals[key] = []
            report[key] = {"state": "invalid"}

    clashes = defaultdict(set)
    keys = list(proposals)
    for i, key in enumerate(keys):
        for other in keys[:i]:
            for row in proposals[key]:
                for previous in proposals[other]:
                    if domain_scope.covers(row, previous) or domain_scope.covers(previous, row):
                        clashes[key].add(row)
                        clashes[other].add(previous)
    for key, rows in clashes.items():
        proposals[key] = [row for row in proposals[key] if row not in rows]
        report[key]["cross-product-conflicts"] = len(rows)
        report[key]["admitted"] = len(proposals[key])
        for row in rows:
            report[key]["proofs"].pop(row, None)
    for stats in report.values():
        state = "current"
        if stats.get("pending") or stats.get("cross-product-conflicts"):
            state = "review"
        elif stats.get("inputs-missing"):
            state = "unavailable"
        stats.setdefault("state", state)
    return proposals, report


def verify_report(entries, data, report):
    expected = {key for key, entry in entries.items() if entry.get('discovery')}
    if set(report) != expected:
        raise Invalid('自动发现报告与业务清单不一致')
    for key, stats in report.items():
        if (entries[key].get('mode') == 'compiled'
                and stats.get('state') in ('invalid', 'unavailable')):
            raise Invalid('自动发现来源未完整读取，保留上一版：' + key)
        inputs = {s['source']: s for s in entries[key]['discovery']['inputs']}
        owners=stats.get('reserved-owners',{})
        if (not isinstance(owners,dict) or any(owner==key or owner not in entries or owner not in data
                or type(count) is not int or count<=0 for owner,count in owners.items())
                or sum(owners.values())>stats.get('scope-conflicts',0)):
            raise Invalid('已归属范围的说明与自动发现排除数量不符：'+key)
        for row, proof in stats.get('proofs', {}).items():
            if row.split(',')[0] not in DOMAIN_TYPES or not any(
                    domain_scope.covers(actual, row) for actual in data[key]):
                raise Invalid('自动发现证据没有对应到规则正文：' + key)
            urls = proof['sources']
            if not urls or not set(urls) <= inputs.keys():
                raise Invalid('自动发现证据引用了未声明来源：' + key)
            families = {inputs[url]['family'] for url in urls}
            authority = any(inputs[url].get('authority') for url in urls)
            if (set(proof['families']) != families or bool(proof['authority']) != authority
                    or not authority and len(families) < entries[key]['discovery'].get('minimum-families', 2)):
                raise Invalid('自动发现报告的来源家族或官方依据不成立：' + key)
