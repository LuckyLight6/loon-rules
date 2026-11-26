"""Shared infrastructure and address boundaries read from the repository policy."""
import json,re
from ipaddress import ip_network
from loon_rules import rules
from loon_rules.project import ROOT

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SCOPE_POLICY=json.loads((ROOT/'config/scope-policy.json').read_text())
SHARED_PARENT=frozenset(SCOPE_POLICY["shared-suffixes"])
PROTECTED_NETWORKS=tuple(map(ip_network,SCOPE_POLICY["protected-networks"]))


def overbroad(kind, value, allowed):
    value=value.casefold()
    if kind=='DOMAIN':
        return value in SCOPE_POLICY.get('path-shared-hosts',()) and value not in allowed
    if kind=='DOMAIN-SUFFIX':
        return (value in SHARED_PARENT or '.' not in value) and value not in allowed
    if kind=='DOMAIN-WILDCARD':
        # A subdomain glob does not include the apex but still claims every tenant.
        base=value.removeprefix('*.')
        if (base in SHARED_PARENT or '.' not in base) and base not in allowed: return True
        return any(rules.match_domain('scope-probe.'+root,kind+','+value)
                   for root in SHARED_PARENT if root not in allowed)
    if kind in ('IP-CIDR','IP-CIDR6'):
        net=ip_network(value,strict=False)
        return any(n.version==net.version and n.subnet_of(net) for n in PROTECTED_NETWORKS)
    return False
