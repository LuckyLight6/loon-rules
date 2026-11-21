"""Generate a Host-only Loon plugin from selected, validated service subscriptions."""
import argparse
import json
import re
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit
from loon_rules.domains import covers

from loon_rules.project import ROOT
OUTPUT = ROOT/'plugins'/'public-services-doh.plugin'
LABEL = re.compile(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?')


def names(rows, protected=()):
    result = set()
    for row in rows:
        parts = row.strip().split(',')
        if len(parts) != 2 or parts[0] not in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-WILDCARD'):
            continue
        kind, host = parts
        if kind == 'DOMAIN-WILDCARD':
            if not host.startswith('*.') or '*' in host[2:] or '?' in host:
                continue  # Host maps cannot represent a wildcard inside a label
            host = host[2:]
        labels = host.split('.')
        if len(host)>253 or len(labels)<2 or not all(LABEL.fullmatch(x) for x in labels) or labels[-1] in ('local','internal','localhost','arpa','test','invalid','onion'):
            raise ValueError('DNS scope is not an ordinary public name')
        try:
            ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('IP literal is not a DNS scope')
        if any((kind != 'DOMAIN-WILDCARD' and p == host) or
               (kind != 'DOMAIN' and p.endswith('.'+host)) for p in protected):
            raise ValueError('DNS scope would claim a protected shared service: '+host)
        if kind != 'DOMAIN-WILDCARD':
            result.add(host)
        if kind != 'DOMAIN':
            result.add('*.'+host)
    return result


def resolver(spec):
    url=spec['resolver']
    dest=urlsplit(url)
    if dest.scheme!='https' or not dest.hostname or dest.username is not None or dest.fragment or dest.query or not dest.path or any(c.isspace() or c in ',#' for c in url):
        raise ValueError('Expected an HTTPS resolver without credentials or parameters')
    provider=spec['provider']
    if not provider or len(provider.splitlines())!=1:
        raise ValueError('Expected a one-line resolver name')
    return url,provider


def build(catalog=None):
    if catalog is None:
        catalog=json.loads((ROOT/'config/catalog.json').read_text())
    spec=catalog['scoped-dns']
    if 'routes' in spec:
        if any(key in spec for key in ('resolver','provider','groups')):
            raise ValueError('Do not mix legacy DNS settings with routes')
        routes=spec['routes']
        if not isinstance(routes,list) or not routes:raise ValueError('Expected DNS routes')
    else:
        routes=[spec]
    priorities={e['id']:e['priority'] for e in catalog['entries']}
    hosts={};selected=set();notes=[]
    def domain_row(host):return ('DOMAIN-WILDCARD,' if host.startswith('*.') else 'DOMAIN,')+host
    for route in routes:
        url,provider=resolver(route)
        groups=route['groups'];label=route.get('label',provider)
        if not isinstance(label,str) or not label or len(label.splitlines())!=1:
            raise ValueError('Expected a one-line DNS route label')
        if not groups or len(set(groups))!=len(groups) or selected.intersection(groups):
            raise ValueError('Expected distinct service groups')
        selected.update(groups)
        notes.append('# '+label+'：'+provider+'；来源规则组 '+', '.join(f'{priorities[name]:03d}' for name in groups))
        scope=set()
        for name in groups:
            f=ROOT/'rules'/f'{priorities[name]:03d}-{name}.lsr'
            group_scope=names(f.read_text().splitlines(),catalog['shared-negatives'])
            if not group_scope:raise ValueError('Selected group has no public DNS hosts: '+f.name)
            scope.update(group_scope)
        for host in sorted(scope):
            row=domain_row(host)
            if any(other_url!=url and (covers(row,domain_row(other)) or covers(domain_row(other),row))
                   for other,other_url in hosts.items()):
                raise ValueError('Public DNS scopes have conflicting resolvers: '+host)
            hosts[host]=url
    return ('#!name = 公网服务分域 DoH\n'
            '#!desc = 按公开服务范围指定加密解析器，其余名称沿用原设置。DoH 连接出口与查询回落仍由 Loon 设置决定\n'+
            '\n'.join(notes)+'\n\n[Host]\n'+
            ''.join(f'{host} = server:{url}\n' for host,url in sorted(hosts.items())))


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--check',action='store_true')
    a=cli.parse_args()
    result=build()
    if a.check:
        if not OUTPUT.is_file() or OUTPUT.read_text()!=result:
            cli.exit(1,'DNS 插件与当前规则不一致\n')
    else:
        OUTPUT.write_text(result)
    return 0
