"""Discover CNAMEs for already-public service hosts; never read client configuration or return IP rules."""
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
from urllib.parse import urlencode
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid
RESOLVERS = ('https://dns.google/resolve', 'https://cloudflare-dns.com/dns-query')

def public_name(value):
    host = domain_scope.public_host(value)
    if domain_scope.current().registrable(host) is None:
        raise Invalid('CNAME 发现不查询内网名称或公共注册后缀')
    return host

def cname_chain(host, document):
    if document.get('Status') not in (0, 3):
        raise Invalid('公共 DNS 返回错误状态')
    edges = {}
    for row in document.get('Answer', ()):
        if row.get('type') != 5:
            continue
        name = public_name(row['name'])
        target = public_name(row['data'])
        edges.setdefault(name, set()).add(target)
    result = []
    todo = [public_name(host)]
    seen = set(todo)
    while todo:
        current = todo.pop(0)
        for target in sorted(edges.get(current, ())):
            if target not in seen:
                seen.add(target)
                result.append(target)
                todo.append(target)
    return result

def query(host):
    host = public_name(host)
    found = set()
    successes = 0
    for resolver in RESOLVERS:
        params = {'name': host, 'type': 'CNAME'}
        if resolver == RESOLVERS[0]:
            params['edns_client_subnet'] = '0.0.0.0/0'
        url = resolver + '?' + urlencode(params)
        request = subprocess.run(('curl', '-q', '-fsSL', '--compressed', '--proto', '=https', '--proto-redir', '=https', '--max-redirs', '0', '--connect-timeout', '5', '--max-time', '12', '--max-filesize', '100000', '-H', 'Accept: application/dns-json', url), capture_output=True)
        if request.returncode:
            continue
        try:
            found.update(cname_chain(host, json.loads(request.stdout)))
            successes += 1
        except (ValueError, KeyError, TypeError, Invalid):
            continue
    if not successes:
        raise Invalid('公共 CNAME 资料暂不可读取')
    return {'aliases': sorted(found), 'requests': len(RESOLVERS), 'successful-resolvers': successes}

def collect(names, *, follow=None):
    hosts = sorted({public_name(host) for host in names})
    records = {}
    failed = []
    requests = 0

    def fetch(host):
        todo = [host]
        seen = {host}
        found = set()
        count = 0
        unavailable = 0;partial=0
        root_read = False
        while todo:
            name = todo.pop(0)
            try:
                result = query(name)
            except (Invalid, OSError):
                count += len(RESOLVERS)
                unavailable += 1
                continue
            count += result['requests']
            partial+=int(result.get('successful-resolvers',result['requests'])<result['requests'])
            if name == host:
                root_read = True
            found.update(result['aliases'])
            for alias in result['aliases']:
                if alias not in seen and follow is not None and follow(host, alias):
                    seen.add(alias)
                    todo.append(alias)
        return (host, {'aliases': sorted(found), 'requests': count, 'root-read': root_read,
                       'unavailable-lookups': unavailable,'partial-lookups':partial})
    unavailable = 0;partial=0;incomplete=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for host, result in pool.map(fetch, hosts):
            requests += result['requests']
            unavailable += result['unavailable-lookups']
            partial += result['partial-lookups']
            if not result['root-read']:
                failed.append(host)
            else:
                records[host] = result['aliases']
                if result['unavailable-lookups'] or result['partial-lookups']:incomplete.append(host)
    return (records, {'hosts-requested': len(hosts), 'hosts-read': len(records), 'http-requests': requests,
                     'unavailable-hosts': len(failed), 'unavailable-lookups': unavailable,
                     'partial-lookups':partial,'incomplete-hosts':incomplete})
