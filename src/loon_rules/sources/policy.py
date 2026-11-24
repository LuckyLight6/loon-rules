"""Validate source evidence policies before downloading or building rules."""
import re
from loon_rules import domains as domain_scope

from loon_rules.rules import Invalid, valid_host


FAMILY = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
DOMAIN_KINDS = {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-WILDCARD'}


def publication_kinds(entry):
    kinds = set(entry.get('publish-kinds', entry['kinds']))
    if entry.get('discovery'):
        kinds.update(DOMAIN_KINDS)
    return kinds


def input_kinds(entry):
    kinds = set(entry['kinds'])
    if entry.get('discovery'):
        kinds.update(DOMAIN_KINDS)
    return kinds


def rule_feeds(entry):
    if 'feed-sources' in entry:
        return entry['feed-sources']
    if spec := entry.get('discovery'):
        return [source['source'] for source in spec['inputs'] if not source.get('recipe')]
    return entry['sources']


def validate(config, entries):
    policies = config.get('source-alias-policies', {})
    for name, policy in policies.items():
        parents = policy.get('parents', {})
        modifiers = policy.get('label-modifiers', [])
        prefixes = policy.get('label-prefixes', [])
        if (not parents or not modifiers and not prefixes
                or not isinstance(modifiers,list) or not isinstance(prefixes,list)
                or any(not isinstance(value,str) or not FAMILY.fullmatch(value) for value in [*modifiers,*prefixes])
                or len(prefixes)!=len(set(prefixes))):
            raise Invalid('别名策略缺少服务范围或标签：' + name)
        for parent, aliases in parents.items():
            if not valid_host(parent) or not aliases or any(not valid_host(a) for a in aliases):
                raise Invalid('别名策略只能使用明确的域名后缀：' + name)
        for parent,suffixes in policy.get('cname-tenants',{}).items():
            if (parent not in parents or not suffixes or any(not valid_host(suffix)
                    or domain_scope.current().suffix(suffix)!=(suffix,True) for suffix in suffixes)):
                raise Invalid('CNAME 租户需要已有服务范围和公共后缀表中的私有后缀：'+name)

    for key, entry in entries.items():
        declared = set(entry.get('sources', ()))
        if spec := entry.get('discovery'):
            if (entry['mode'] not in ('compiled', 'managed') or entry.get('fallback')
                    or entry.get('policy-hint') == 'reject'):
                raise Invalid('自动发现只能用于独立业务表：' + key)
            threshold = spec.get('minimum-families', 2)
            if type(threshold) is not int or threshold < 2:
                raise Invalid('非官方候选至少需要两个独立来源家族：' + key)
            inputs = spec.get('inputs', ())
            if not inputs:
                raise Invalid('自动发现缺少输入：' + key)
            seen = set()
            for source in inputs:
                url = source.get('source')
                authority = source.get('authority', False)
                if (url not in declared or url in seen
                        or not FAMILY.fullmatch(source.get('family', ''))):
                    raise Invalid('自动发现的来源、家族或重复关系无效：' + key)
                seen.add(url)
                recipe = source.get('recipe')
                if (type(authority) is not bool or authority and not recipe
                        or recipe and (not recipe.get('format') or
                                       recipe.get('source', url) != url)):
                    raise Invalid('官方依据必须限定资料用途与来源：' + key)
        if spec := entry.get('aliases'):
            if (entry['mode'] != 'compiled' or spec.get('policy') not in policies
                    or not set(spec.get('sources', ())) <= declared
                    or type(spec.get('resolve-cname', False)) is not bool
                    or type(spec.get('protect-from-reject', False)) is not bool):
                raise Invalid('服务别名缺少策略、公开来源或合法开关：' + key)
