"""Use the Public Suffix List to distinguish a product root from a registry or cloud suffix."""
from pathlib import Path
from ipaddress import ip_address
from datetime import datetime
import re
from loon_rules.rules import Invalid, valid_host, match_domain
from loon_rules.project import ROOT

DATA = ROOT / 'data' / 'public-suffix-list.dat'

def public_host(value):
    try:
        host = value.removesuffix('.').encode('idna').decode('ascii').casefold()
    except UnicodeError as exc:
        raise Invalid('公开主机名编码无效') from exc
    try:
        ip_address(host)
    except ValueError:
        pass
    else:
        raise Invalid('公开域名来源不能使用 IP 字面量')
    suffixes = current()
    if not valid_host(host) or host.split('.')[-1] not in suffixes.icann_tlds:
        raise Invalid('来源不是已注册公共后缀下的域名')
    suffix, private = suffixes.suffix(host)
    if host == suffix and (not private):
        raise Invalid('公共注册后缀不能归给产品')
    return host

def fixed_tail(host):
    labels = []
    for label in reversed(host.split('.')):
        if re.search('[*?\\[\\]]', label):
            break
        labels.insert(0, label)
    return '.'.join(labels)

def covers(parent, child):
    if parent == child:
        return True
    kind, host, *flags = parent.split(',')
    other, name, *extra = child.split(',')
    if flags or extra:
        return False
    fixed = fixed_tail(name)
    if kind == 'DOMAIN-SUFFIX' and other in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-WILDCARD'):
        return fixed == host or fixed.endswith('.' + host)
    if kind == 'DOMAIN-WILDCARD' and other == 'DOMAIN':
        return match_domain(name,parent)
    if kind == 'DOMAIN-WILDCARD' and host.startswith('*.') and (not re.search('[*?\\[\\]]', host[2:])):
        root = host[2:]
        return fixed.endswith('.' + root) or (other == 'DOMAIN-WILDCARD' and fixed == root and (name != root))
    return False

def exclude_shared_scopes(rows, scopes):
    protected = [('DOMAIN-WILDCARD,' if '*' in host else 'DOMAIN,') + host for host in scopes]
    return [row for row in rows if not any((covers(row, reference) for reference in protected))]

class Suffixes:

    def __init__(self, text):
        self.exact = {}
        self.wild = {}
        self.exceptions = {}
        self.icann_tlds = set()
        private = False
        for raw in text.splitlines():
            line = raw.strip()
            if line == '// ===BEGIN PRIVATE DOMAINS===':
                private = True
            if not line or line.startswith('//'):
                continue
            target = self.exceptions if line.startswith('!') else self.wild if line.startswith('*.') else self.exact
            rule = line.removeprefix('!').removeprefix('*.')
            rule = '.'.join((label.encode('idna').decode('ascii') for label in rule.split('.'))).casefold()
            target[rule] = private
            if not private:
                self.icann_tlds.add(rule.rsplit('.', 1)[-1])
        if not self.exact:
            raise ValueError('公共后缀表为空')

    def suffix(self, host):
        labels = host.casefold().split('.')
        length = 1
        private = False
        for i in range(len(labels)):
            name = '.'.join(labels[i:])
            size = len(labels) - i
            if name in self.exceptions:
                return ('.'.join(labels[i + 1:]), self.exceptions[name])
            if name in self.exact and size >= length:
                length = size
                private = self.exact[name]
            if name in self.wild and i and (size + 1 >= length):
                length = size + 1
                private = self.wild[name]
        return ('.'.join(labels[-length:]), private)

    def registrable(self, host):
        suffix, _ = self.suffix(host)
        labels = host.casefold().split('.')
        count = len(suffix.split('.')) + 1
        return '.'.join(labels[-count:]) if len(labels) >= count else None
_current = None

def current():
    global _current
    if _current is None:
        _current = Suffixes(DATA.read_text())
    return _current

def complete_list(text):
    if not all((marker in text for marker in ('// ===BEGIN ICANN DOMAINS===', '// ===END ICANN DOMAINS===', '// ===BEGIN PRIVATE DOMAINS===', '// ===END PRIVATE DOMAINS==='))):
        raise ValueError('公共后缀表缺少完整的注册与私有托管章节')
    candidate = Suffixes(text)
    if not all((name in candidate.exact for name in ('com', 'co.uk', 'github.io'))):
        raise ValueError('公共后缀表缺少已知的基础后缀')
    return candidate

def select_list(incoming, previous):
    """Keep a newer published PSL when an edge cache returns an older dated copy."""
    complete_list(incoming)
    def version(text):
        found=re.findall(r'^// VERSION: (\S+)\s*$',text,re.M)
        if len(found)!=1:raise ValueError('公共后缀表缺少唯一版本时间')
        try:datetime.strptime(found[0],'%Y-%m-%d_%H-%M-%S_UTC')
        except ValueError as error:raise ValueError('公共后缀表的版本时间无效') from error
        return found[0]
    fresh=version(incoming)
    if previous:
        complete_list(previous)
        active=version(previous)
        if fresh<active:
            return previous,{'state':'retained-newer','source-version':fresh,'active-version':active}
    return incoming,{'state':'current','source-version':fresh,'active-version':fresh}

def use(text):
    global _current
    _current = complete_list(text)
