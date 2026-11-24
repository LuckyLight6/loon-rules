"""Approve region and advertising changes using evidence with the same matching scope."""
from bisect import bisect_right
from ipaddress import IPv4Address, IPv6Address, ip_address, ip_network, summarize_address_range
import re

from loon_rules.rules import Invalid


def merged(spans):
    out=[]
    for a,b in sorted(spans):
        if out and a<=out[-1][1]+1: out[-1]=(out[-1][0],max(b,out[-1][1]))
        else: out.append((a,b))
    return out


def difference(left,right):
    result=[]; j=0
    for a,b in left:
        while j<len(right) and right[j][1]<a: j+=1
        i=j
        while i<len(right) and right[i][0]<=b:
            x,y=right[i]
            if x>a: result.append((a,x-1))
            a=max(a,y+1)
            if a>b: break
            i+=1
        if a<=b: result.append((a,b))
    return result


def network_ranges(lines,*,rows=False):
    out={4:[],6:[]}
    for line in lines:
        if rows:
            vals=line.split(',')
            if len(vals)!=2 or vals[0] not in ('IP-CIDR','IP-CIDR6'):
                raise Invalid('网段交叉核对只用于允许解析的纯 CIDR 表')
            line=vals[1]
        net=ip_network(line)
        if not net.is_global or net.prefixlen==0: raise Invalid('网段来源含非公网地址')
        out[net.version].append((int(net.network_address),int(net.broadcast_address)))
    return {v:merged(spans) for v,spans in out.items()}


def allocations(text):
    out={4:[],6:[]}
    for line in text.splitlines():
        f=line.split('|')
        if len(f)<7 or f[:2]!=['apnic','CN'] or f[2] not in ('ipv4','ipv6') or f[6] not in ('assigned','allocated'): continue
        if f[2]=='ipv4':
            a=int(IPv4Address(f[3])); b=a+int(f[4])-1
            if b<a or b>=2**32: raise Invalid('IPv4 分配记录范围有误')
            out[4].append((a,b))
        else:
            net=ip_network(f[3]+'/'+f[4])
            if net.version!=6: raise Invalid('IPv6 分配记录格式有误')
            out[6].append((int(net.network_address),int(net.broadcast_address)))
    return {v:merged(spans) for v,spans in out.items()}


def networks(old,source,registry,routes):
    before=network_ranges(old,rows=True); wanted=network_ranges(source,rows=True)
    reg=allocations(registry); bgp=network_ranges(routes.split())
    def size(spans): return sum(b-a+1 for a,b in spans)
    counts={'accepted-prefixes':0,'unconfirmed-prefixes':0,'retired-prefixes':0}
    out=[]; changed=False
    for v,addr,kind in [(4,IPv4Address,'IP-CIDR'),(6,IPv6Address,'IP-CIDR6')]:
        def prefixes(spans):
            return [kind+','+str(net) for a,b in spans for net in summarize_address_range(addr(a),addr(b))]
        if not all(x[v] for x in (before,wanted,reg,bgp)): raise Invalid('网段数据缺少完整地址族')
        unconfirmed=merged(difference(wanted[v],reg[v])+difference(wanted[v],bgp[v]))
        approved=difference(wanted[v],unconfirmed)
        adds=difference(approved,before[v]); drops=difference(before[v],approved)
        if 20*max(size(adds),size(drops))>size(before[v]): raise Invalid('网段变动超过原地址空间的 5%')
        counts['accepted-prefixes']+=len(prefixes(adds))
        counts['unconfirmed-prefixes']+=len(prefixes(unconfirmed))
        counts['retired-prefixes']+=len(prefixes(drops))
        changed|=bool(adds or drops)
        # Preserve upstream segmentation; split a prefix only where corroboration stops.
        stop=[x for x,_ in unconfirmed]
        for row in source:
            if not row.startswith(kind+','): continue
            net=ip_network(row.split(',')[1]); a,b=int(net.network_address),int(net.broadcast_address)
            j=bisect_right(stop,b)
            if not j or unconfirmed[j-1][1]<a: out.append(row)
            else:
                i=max(0,bisect_right(stop,a)-1)
                out.extend(prefixes(difference([(a,b)],unconfirmed[i:j])))
    return (out if changed else old),counts


def confirmed_ads(rows,sources,*,reviewed=()):
    agree=None; exceptions=set();unconditional=set()
    for text in sources:
        whole=set()
        for line in text.splitlines():
            if (m:=re.fullmatch(r'\|\|([a-z0-9.-]+)\^',line)): whole.add(m[1])
            elif (m:=re.match(r'@@(?:\|\||\|https?://)([a-z0-9.-]+)(?=[/\^$|:]|$)',line)):
                exceptions.add(m[1])
                if re.fullmatch(r'@@\|\|[a-z0-9.-]+\^',line):unconditional.add(m[1])
        if not whole: raise Invalid('广告核对源不含整域规则')
        agree=whole if agree is None else agree & whole
    def parents(host):
        parts=host.split('.')
        return ('.'.join(parts[i:]) for i in range(len(parts)))
    ancestors={p for h in exceptions for p in parents(h)}
    baseline_ancestors={p for h in unconditional for p in parents(h)}
    addresses=[]
    for host in unconditional:
        try:addresses.append(ip_address(host))
        except ValueError:pass
    baseline=set(reviewed)
    confirmed=[]
    for row in dict.fromkeys([*rows,*reviewed]):
        kind,host,*flags=row.split(',')
        if kind in ('IP-CIDR','IP-CIDR6'):
            if row in baseline and not any(address in ip_network(host) for address in addresses):
                confirmed.append(row)
            continue
        if kind not in ('DOMAIN','DOMAIN-SUFFIX') or flags or (host not in agree and row not in baseline):continue
        # Contextual page exceptions cannot globally unblock a reviewed DNS rule.
        allowed=unconditional if row in baseline else exceptions
        upper=baseline_ancestors if row in baseline else ancestors
        if any(p in allowed for p in parents(host)) or (kind=='DOMAIN-SUFFIX' and host in upper):continue
        confirmed.append(row)
    return confirmed


def withdrawals(last, current, previous, revision, now):
    """Retire small, complete domain withdrawals; never expand membership from one feed."""
    exact=set(); suffix=set(); ancestors=set()
    # Refuse to remove a domain still covered by a parent or refined to children.
    for row in current:
        kind,host,*flags=row.lower().split(',')
        if kind not in ('domain','domain-suffix') or flags:continue
        exact.add(host)
        if kind=='domain-suffix':suffix.add(host)
        parts=host.split('.')
        ancestors.update('.'.join(parts[i:]) for i in range(1,len(parts)))
    gone=[]
    for i,row in enumerate(last):
        kind,host,*flags=row.lower().split(',')
        if kind not in ('domain','domain-suffix') or flags or host in exact:continue
        parts=host.split('.')
        if any('.'.join(parts[k:]) in suffix for k in range(1,len(parts))):continue
        if kind=='domain-suffix' and host in ancestors:continue
        gone.append(i)
    if not gone or len(gone)>max(1,len(last)//20):return last,{}
    eligible=(previous.get('body')==revision and 0<=now-previous.get('last-read',-1)<=3*86400)
    first=previous.get('first',{}) if eligible else {}
    since={str(i):first.get(str(i),now) for i in gone}
    drop={i for i in gone if now-since[str(i)]>=20*3600}
    result=[row for i,row in enumerate(last) if i not in drop]
    if not result:return last,{}
    # Only positions in the previously published file, never candidate names.
    return result,({} if drop else {'body':revision,'first':since,'last-read':now})


def asn_additions(last,current,witness,registry):
    """Require an explicit ASN in both feeds and a matching APNIC CN allocation."""
    agreed={int(m[1]) for line in witness.splitlines()
            if (m:=re.fullmatch(r'IP-ASN,(\d+)(?:,no-resolve)?',line.strip(),re.I))}
    allocations=[]
    for line in registry.splitlines():
        p=line.split('|')
        if (len(p)>=7 and p[:3]==['apnic','CN','asn'] and p[6] in ('allocated','assigned')
                and p[3].isdigit() and p[4].isdigit() and int(p[4])>0):
            allocations.append((int(p[3]),int(p[3])+int(p[4])-1))
    if not agreed or not allocations:raise Invalid('缺少 ASN 来源或中国分配记录')
    spans=merged(allocations);starts=[s for s,_ in spans]
    out=list(last);known=set(last);unconfirmed=0
    for row in current:
        if row in known:continue
        n=int(row.split(',')[1]);i=bisect_right(starts,n)-1
        if n in agreed and i>=0 and n<=spans[i][1]:
            out.append(row);known.add(row)
        else:unconfirmed+=1
    return out,{'admitted-asns':len(out)-len(last),'unconfirmed-asns':unconfirmed}
