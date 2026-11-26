"""Read complete community inputs without changing their matching semantics."""
import json
import re
from ipaddress import ip_network

from loon_rules import domains, rules

FORMATS = {'classical', 'quantumult-x', 'domain-set', 'clash-domain', 'clash-classical', 'clash-domain-lines', 'sing-box'}
JSON_FIELDS = {'domain': 'DOMAIN', 'domain_suffix': 'DOMAIN-SUFFIX', 'domain_keyword': 'DOMAIN-KEYWORD',
    'domain_regex': 'DOMAIN-REGEX', 'ip_cidr': 'IP-CIDR', 'ip_asn': 'IP-ASN',
    'source_ip_cidr': 'SRC-IP-CIDR', 'process_name': 'PROCESS-NAME', 'process_path': 'PROCESS-PATH',
    'process_path_regex': 'PROCESS-PATH-REGEX', 'package_name': 'PACKAGE-NAME',
    'package_name_regex': 'PACKAGE-NAME-REGEX', 'port': 'DEST-PORT', 'port_range': 'DEST-PORT-RANGE',
    'source_port': 'SRC-PORT', 'source_port_range': 'SRC-PORT-RANGE', 'network': 'NETWORK',
    'network_type': 'NETWORK-TYPE', 'network_is_expensive': 'NETWORK-IS-EXPENSIVE',
    'network_is_constrained': 'NETWORK-IS-CONSTRAINED', 'network_interface_address': 'NETWORK-INTERFACE-ADDRESS',
    'default_interface_address': 'DEFAULT-INTERFACE-ADDRESS', 'wifi_ssid': 'WIFI-SSID', 'wifi_bssid': 'WIFI-BSSID'}
OPTIONS = {'no-resolve', 'extended-matching', 'pre-matching', 'force-remote-dns'}


def canonical(kind, value, options=()):
    kind = {'IP6-CIDR': 'IP-CIDR6'}.get(kind.upper(), kind.upper())
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise rules.Invalid('社区规则的值不是文字或数字')
    value = str(value).strip()
    if not value or any(character in value for character in '\r\n') or set(options) - OPTIONS:
        raise rules.Invalid('社区规则缺少完整的值或含未知参数')
    if kind in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-WILDCARD', 'DOMAIN-KEYWORD'):
        value = value.casefold()
        if not re.fullmatch(r'[a-z0-9_.*?\[\]-]+', value):
            raise rules.Invalid('社区域名规则含未知语法')
        if kind in ('DOMAIN', 'DOMAIN-SUFFIX') and (value.startswith('.') or '*' in value or '?' in value):
            raise rules.Invalid('精确域名和后缀规则不能静默改变通配语义')
    elif kind in ('IP-CIDR', 'IP-CIDR6', 'SRC-IP-CIDR'):
        network = ip_network(value, strict=False)
        if kind == 'IP-CIDR' and network.version == 6:
            kind = 'IP-CIDR6'
        if kind == 'IP-CIDR6' and network.version != 6:
            raise rules.Invalid('IPv6 类型与地址不一致')
        # Native clients mask host bits; retain that fact in normalize() notes.
        value = str(network)
    elif kind == 'IP-ASN':
        if not value.isdecimal() or not 0 < int(value) < 4294967295:
            raise rules.Invalid('社区 ASN 无效')
        value = str(int(value))
    elif kind not in {'PROCESS-NAME', 'PROCESS-PATH', 'USER-AGENT', 'URL-REGEX', 'DOMAIN-REGEX',
            'PACKAGE-NAME', 'GEOIP', 'DEST-PORT', 'DEST-PORT-RANGE', 'SRC-PORT', 'SRC-PORT-RANGE', 'NETWORK'}:
        raise rules.Invalid('未确认社区规则类型：' + kind)
    return ','.join([kind, value, *options])


def logical(value):
    kind, _, body = value.partition(',')
    if kind not in ('AND', 'OR', 'NOT') or not body.startswith('(') or not body.endswith(')'):
        raise rules.Invalid('逻辑规则缺少完整结构')
    depth = 0
    for character in body:
        depth += (character == '(') - (character == ')')
        if depth < 0:
            raise rules.Invalid('逻辑规则括号不平衡')
    if depth:
        raise rules.Invalid('逻辑规则括号不平衡')
    return value


def payload(text):
    result = []
    found = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if not found:
            if line != 'payload:':
                raise rules.Invalid('YAML 规则集不是明确的 payload 列表')
            found = True
            continue
        if not raw[:1].isspace() or not line.startswith('- '):
            raise rules.Invalid('YAML 规则集含未确认字段或结构')
        value = line[2:].strip()
        if value.startswith('"'):
            value = json.loads(value)
        elif value.startswith("'"):
            if not value.endswith("'"):
                raise rules.Invalid('YAML 规则集引号不完整')
            value = value[1:-1].replace("''", "'")
        if not isinstance(value, str) or not value:
            raise rules.Invalid('YAML 规则集条目无效')
        result.append(value)
    if not found or not result:
        raise rules.Invalid('YAML 规则集为空')
    return result


def normalize(form, text):
    if form not in FORMATS:
        raise rules.Invalid('社区来源尚未确认格式：' + form)
    atoms = set()
    conditions = []
    policies = {}
    notes = set()
    if form == 'sing-box':
        doc = json.loads(text)
        if (not isinstance(doc, dict) or set(doc) != {'version', 'rules'}
                or type(doc['version']) is not int or doc['version'] not in (1, 2, 3, 4, 5)
                or not isinstance(doc['rules'], list) or not doc['rules']):
            raise rules.Invalid('sing-box 来源缺少必需版本或完整规则结构')
        def validate(item):
            if not isinstance(item, dict) or not item:
                raise rules.Invalid('sing-box 条件为空')
            if item.get('type') == 'logical':
                if (set(item) - {'type', 'mode', 'rules', 'invert'} or item.get('mode') not in ('and', 'or')
                        or type(item.get('invert', False)) is not bool
                        or not isinstance(item.get('rules'), list) or not item['rules']):
                    raise rules.Invalid('sing-box 逻辑结构不完整')
                for child in item['rules']:
                    validate(child)
            elif (set(item) - set(JSON_FIELDS) - {'invert'} or not set(item) & set(JSON_FIELDS)
                    or type(item.get('invert', False)) is not bool):
                raise rules.Invalid('sing-box 来源含未确认字段')
            else:
                for field in set(item) & set(JSON_FIELDS):
                    value = item[field]
                    if value is None or isinstance(value, list) and not value:
                        raise rules.Invalid('sing-box 条件的值为空')
        simple = {'domain', 'domain_suffix', 'domain_keyword', 'ip_cidr', 'ip_asn', 'process_name'}
        for item in doc['rules']:
            validate(item)
            fields = set(item) & set(JSON_FIELDS)
            if item.get('type') == 'logical' or item.get('invert') or len(fields) != 1 or not fields <= simple:
                conditions.append(item)
                continue
            field = next(iter(fields))
            values = item[field] if isinstance(item[field], list) else [item[field]]
            for value in values:
                kind = JSON_FIELDS[field]
                if field == 'domain_suffix' and isinstance(value, str) and value.startswith('.'):
                    kind, value = 'DOMAIN-WILDCARD', '*' + value
                atoms.add(canonical(kind, value))
    else:
        lines = payload(text) if form in ('clash-domain', 'clash-classical') else text.splitlines()
        for raw in lines:
            line = raw.strip().lstrip('\ufeff').strip()
            if not line or line.startswith(('#', '//', ';')):
                continue
            if form in ('domain-set', 'clash-domain', 'clash-domain-lines'):
                if line.startswith('+.' ) and form in ('clash-domain', 'clash-domain-lines'):
                    row = canonical('DOMAIN-SUFFIX', line[2:])
                elif line.startswith('.'):
                    row = canonical('DOMAIN-SUFFIX' if form == 'domain-set' else 'DOMAIN-WILDCARD',
                                    line[1:] if form == 'domain-set' else '*' + line)
                elif '*' in line or '?' in line:
                    if form == 'domain-set':
                        raise rules.Invalid('Surge DOMAIN-SET 不接受未声明的通配扩展')
                    # Clash's * matches one label, unlike DOMAIN-WILDCARD's arbitrary characters.
                    conditions.append({'clash-domain': line})
                    continue
                else:
                    row = canonical('DOMAIN', line)
            elif line.partition(',')[0] in ('AND', 'OR', 'NOT'):
                conditions.append(logical(line))
                continue
            else:
                fields = [field.strip() for field in line.split(',')]
                if len(fields) < 2:
                    raise rules.Invalid('社区来源不是完整的类型规则')
                kind, value, *options = fields
                if form == 'quantumult-x':
                    kind = {'HOST': 'DOMAIN', 'HOST-SUFFIX': 'DOMAIN-SUFFIX',
                        'HOST-KEYWORD': 'DOMAIN-KEYWORD', 'HOST-WILDCARD': 'DOMAIN-WILDCARD'}.get(kind.upper(), kind)
                    if not options or not options[0]:
                        raise rules.Invalid('Quantumult X 来源缺少策略上下文')
                    policy, *options = options
                row = canonical(kind, value, options)
                if form == 'quantumult-x':
                    if row in policies and policies[row] != policy:
                        raise rules.Invalid('同一 Quantumult X 条件带有冲突策略')
                    policies[row] = policy
                if kind.upper() in ('IP-CIDR', 'IP-CIDR6', 'IP6-CIDR') and row.split(',')[1] != value:
                    notes.add('unaligned-or-noncanonical-ip-prefix')
            atoms.add(row)
    if not atoms and not conditions:
        raise rules.Invalid('完整社区来源没有规则条件')
    return {'rules': sorted(atoms), 'conditions': conditions, 'policies': policies, 'notes': sorted(notes)}


def contributions(identity, current, upstreams):
    """Keep inheritance, narrowing, expansion, withdrawal and classification as separate evidence."""
    baseline = {} if upstreams is None else {row: sorted(key for key, source in upstreams.items() if row in source['rules'])
        for source in upstreams.values() for row in source['rules']}
    entries = []
    for row in current['rules']:
        inherited = baseline.get(row, [])
        narrower = [old for old in baseline if old != row and domains.covers(old, row)]
        wider = [old for old in baseline if old != row and domains.covers(row, old)]
        changed_category = bool(inherited) and any(set(upstreams[key].get('products', ())) != set(current.get('products', ()))
                                                   for key in inherited)
        change = 'inherited' if inherited else 'narrowed' if narrower else 'expanded' if wider else 'added'
        policy=current.get('policies',{}).get(row)
        prior_policies={key:upstreams[key].get('policies',{}).get(row) for key in inherited}
        changed_policies={key:value for key,value in prior_policies.items()
                          if policy is not None and value is not None and value!=policy}
        contributors=list(inherited) if inherited else ([identity] if upstreams is not None else [])
        if changed_policies:contributors.append(identity)
        entries.append({'rule': row, 'change': change, 'inherited-from': inherited,
            'contributors': contributors,
            'classification-contributors': [identity] if changed_category else [],
            'policy-contributors':[identity] if changed_policies else [],
            'policy-change':{'from':changed_policies,'to':policy} if changed_policies else None,
            'policy-context-complete':bool(prior_policies) and policy is not None and all(value is not None for value in prior_policies.values()),
            'scope-baseline': narrower or wider})
    removed = [row for row in baseline if not any(domains.covers(new, row) for new in current['rules'])]
    return {'independence': 'unverified' if upstreams is None else 'compared-to-declared-upstreams',
        'entries': entries, 'removed': sorted(removed),
        'removed-contributors': [identity] if removed else []}
