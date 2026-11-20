"""Generate a Host-only Loon plugin from selected, validated service subscriptions."""
import argparse
import json
import re
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
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


def build(catalog=None):
    if catalog is None:
        catalog=json.loads((ROOT/'catalog.json').read_text())
    spec=catalog['scoped-dns']
    url=spec['resolver']
    dest=urlsplit(url)
    if dest.scheme!='https' or not dest.hostname or dest.username is not None or dest.fragment or dest.query or not dest.path or any(c.isspace() or c in ',#' for c in url):
        raise ValueError('Expected an HTTPS resolver without credentials or parameters')
    provider=spec['provider']
    if not provider or len(provider.splitlines())!=1:
        raise ValueError('Expected a one-line resolver name')
    groups=spec['groups']
    if not groups or len(set(groups))!=len(groups):
        raise ValueError('Expected distinct service groups')
    priorities={e['id']:e['priority'] for e in catalog['entries']}
    hosts=set()
    for name in groups:
        n=priorities[name]
        f=ROOT/'rules'/f'{n:03d}-{name}.lsr'
        scope=names(f.read_text().splitlines(),catalog['shared-negatives'])
        if not scope: raise ValueError('Selected group has no public DNS hosts: '+f.name)
        hosts.update(scope)
    return (f'#!name = 公网服务分域 DoH\n#!desc = 指定服务使用{provider} 的 HTTPS 入口，其余名称沿用原设置。严格模式请在 Loon 的 DNS 服务器页关闭查询回落\n'
            '# 来源规则组：'+', '.join(f'{n:03d}' for n in (priorities[name] for name in groups))+'\n\n[Host]\n'+
            ''.join(f'{h} = server:{url}\n' for h in sorted(hosts)))


if __name__ == '__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--check',action='store_true')
    a=cli.parse_args()
    result=build()
    if a.check:
        if not OUTPUT.is_file() or OUTPUT.read_text()!=result:
            cli.exit(1,'DNS 插件与当前规则不一致\n')
    else:
        OUTPUT.write_text(result)
