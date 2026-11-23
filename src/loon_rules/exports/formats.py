"""Translate matching conditions without changing service ownership or DNS intent."""
from itertools import product
import re

from loon_rules.rules import Invalid, IP_TYPES, read_rules


class Unsupported(Invalid):
    """A target cannot express the complete canonical rule group."""


def glob_tokens(pattern):
    """Keep glob operators distinct from literal characters and finite classes."""
    position = 0
    while position < len(pattern):
        char = pattern[position]
        closing_start = position + 2 if pattern[position + 1:position + 2] == ']' else position + 1
        if char != '[' or ']' not in pattern[closing_start:]:
            yield char
            position += 1
            continue
        end = pattern.index(']', closing_start)
        body = pattern[position + 1:end]
        if not body:
            yield '['
            position += 1
            continue
        choices = []
        offset = 0
        while offset < len(body):
            if offset + 2 < len(body) and body[offset + 1] == '-':
                start, stop = ord(body[offset]), ord(body[offset + 2])
                if start > stop:
                    raise Unsupported('通配符字符范围不能等价转换：' + pattern)
                choices.extend(chr(value) for value in range(start, stop + 1))
                offset += 3
            else:
                choices.append(body[offset])
                offset += 1
        yield tuple(dict.fromkeys(choices))
        position = end + 1


def glob_regex(pattern):
    parts = []
    for token in glob_tokens(pattern):
        if isinstance(token, tuple):
            parts.append('[' + ''.join(re.escape(char) for char in token) + ']')
        elif token == '*':
            parts.append('.*')
        elif token == '?':
            parts.append('.')
        else:
            parts.append(re.escape(token))
    return '(?i)^' + ''.join(parts) + '$'


def expand_classes(pattern, limit=10000):
    tokens = list(glob_tokens(pattern))
    size = 1
    for token in tokens:
        if isinstance(token, tuple):
            if any(char in '*?' for char in token):
                raise Unsupported('客户端无法保留字符类里的通配符字面字符：' + pattern)
            size *= len(token)
            if size > limit:
                raise Unsupported('通配符展开超过客户端输出上限：' + pattern)
    return [''.join(parts) for parts in product(*[
        token if isinstance(token, tuple) else (token,) for token in tokens
    ])]


def convert(target, rows):
    parsed = [row.split(',') for row in read_rules('\n'.join(rows))]
    for kind, value, *flags in parsed:
        if 'extended-matching' in flags:
            raise Unsupported(target + ' 未确认 extended-matching 的等价行为')
        if flags and kind not in IP_TYPES:
            raise Unsupported(target + ' 无法等价转换域名附加参数：' + kind)
        if target in ('sing-box', 'v2ray') and kind in IP_TYPES:
            raise Unsupported(target + ' 无法在这份独立规则中保留 ' + kind +
                              ' 的 ASN、GeoIP 或逐条 DNS 匹配行为')
        if target == 'quantumult-x' and 'no-resolve' in flags:
            raise Unsupported('Quantumult X 没有已确认的逐条 no-resolve 参数：' + kind)
        if target == 'surfboard' and kind == 'IP-ASN':
            raise Unsupported('Surfboard 官方规则类型未列出 IP-ASN')
        if kind not in {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD',
                        'DOMAIN-WILDCARD', *IP_TYPES}:
            raise Unsupported(target + ' 尚未支持 ' + kind)
    if target in ('loon', 'surge'):
        return [','.join(parts) for parts in parsed]
    if target == 'clash-classical':
        return {'payload': [
            'DOMAIN-REGEX,' + glob_regex(value) if kind == 'DOMAIN-WILDCARD'
            else ','.join((kind, value, *flags)) for kind, value, *flags in parsed
        ]}
    if target in ('surfboard', 'shadowrocket', 'quantumult-x'):
        names = {'DOMAIN': 'host', 'DOMAIN-SUFFIX': 'host-suffix',
                 'DOMAIN-KEYWORD': 'host-keyword', 'DOMAIN-WILDCARD': 'host-wildcard',
                 'IP-CIDR': 'ip-cidr', 'IP-CIDR6': 'ip6-cidr',
                 'IP-ASN': 'ip-asn', 'GEOIP': 'geoip'}
        result = []
        for kind, value, *flags in parsed:
            values = expand_classes(value) if kind == 'DOMAIN-WILDCARD' else [value]
            for item in values:
                result.append(','.join((names[kind], item, 'proxy')) if target == 'quantumult-x'
                              else ','.join((kind, item, *flags)))
        return result
    if target == 'egern':
        fields = {'DOMAIN': 'domain_set', 'DOMAIN-SUFFIX': 'domain_suffix_set',
                  'DOMAIN-KEYWORD': 'domain_keyword_set', 'DOMAIN-WILDCARD': 'domain_regex_set',
                  'IP-CIDR': 'ip_cidr_set', 'IP-CIDR6': 'ip_cidr6_set',
                  'IP-ASN': 'asn_set', 'GEOIP': 'geoip_set'}
        main, literal = {}, {}
        for kind, value, *flags in parsed:
            node = literal if 'no-resolve' in flags else main
            if kind == 'IP-ASN':
                value = 'AS' + value
            elif kind == 'DOMAIN-WILDCARD':
                value = glob_regex(value)
            node.setdefault(fields[kind], []).append(value)
        if literal:
            if any(kind in IP_TYPES and not flags for kind, _, *flags in parsed):
                main['or_set'] = [{'no_resolve': True, **literal}]
            else:
                main = {'no_resolve': True, **main, **literal}
        return main
    if target == 'sing-box':
        fields = {'DOMAIN': 'domain', 'DOMAIN-SUFFIX': 'domain_suffix',
                  'DOMAIN-KEYWORD': 'domain_keyword', 'DOMAIN-WILDCARD': 'domain_regex'}
        rule = {}
        for kind, value, *_ in parsed:
            rule.setdefault(fields[kind], []).append(glob_regex(value) if kind == 'DOMAIN-WILDCARD' else value)
        return {'version': 1, 'rules': [rule]}
    if target == 'v2ray':
        prefixes = {'DOMAIN': 'full:', 'DOMAIN-SUFFIX': 'domain:',
                    'DOMAIN-KEYWORD': '', 'DOMAIN-WILDCARD': 'regexp:'}
        values = [prefixes[kind] + (glob_regex(value) if kind == 'DOMAIN-WILDCARD' else value)
                  for kind, value, *_ in parsed]
        return {'routing': {'rules': [{'type': 'field', 'domains': values, 'outboundTag': 'PROXY'}]}}
    raise Invalid('未知客户端规则格式：' + target)


def yaml_text(value, level=0):
    """Write the small, explicit YAML subset used by the two native schemas."""
    import json
    indent = ' ' * level
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(indent + key + ':')
                lines.append(yaml_text(item, level + 2))
            else:
                lines.append(indent + key + ': ' + json.dumps(item, ensure_ascii=False))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(indent + '-')
                lines.append(yaml_text(item, level + 2))
            else:
                lines.append(indent + '- ' + json.dumps(item, ensure_ascii=False))
    return '\n'.join(lines)
