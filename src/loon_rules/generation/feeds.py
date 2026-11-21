"""Evidence-based updates of reviewed rule feeds."""
from loon_rules import rules
from loon_rules.generation import calibration
from loon_rules.sources import policy as source_policy
from loon_rules.generation.membership import compact,outside_domain_scopes,outside_tenant_scopes,stable_order,uncovered_count,without_protected
from loon_rules.policy import overbroad



def reviewed_input(entry, downloaded, *, audit=None, tenant_roots=(), official=()):
    """Parse licensed source material, keeping only the rule kinds we publish."""
    allowed=source_policy.publication_kinds(entry)
    permitted=set(entry.get('allowed-shared',()))
    excluded=set(entry.get('excluded-rules',()))
    current=[]
    unaligned=set()
    client_matches=set()
    tenant_rows=set()
    roots=set(entry.get('exclude-tenant-roots',()))|set(tenant_roots)
    for url in source_policy.rule_feeds(entry):
        for row in rules.read_rules(downloaded[url],source_policy.input_kinds(entry),set(entry['flags'])):
            kind,value,*_=row.split(',')
            if not rules.aligned_network(row):
                unaligned.add(row)
                continue
            if kind not in allowed and kind in ('PROCESS-NAME','USER-AGENT','URL-REGEX'):
                client_matches.add(row)
            if not outside_tenant_scopes([row],roots,official):
                tenant_rows.add(row)
                continue
            if row in excluded or kind not in allowed or overbroad(kind,value,permitted):
                continue
            current.append(row)
    if audit is not None and unaligned:
        audit['unaligned-prefixes']=len(unaligned)
    if audit is not None and client_matches:
        audit['excluded-client-matches']=len(client_matches)
    if audit is not None and tenant_rows:
        audit['outside-purpose']=len(tenant_rows)
    if not current:
        raise rules.Invalid('筛选后没有可用规则：'+entry['id'])
    if include:=entry.get('include'):
        current.extend(rules.read_rules('\n'.join(include),allowed,set(entry['flags'])))
    return compact(current)


def calibration_urls(spec):
    if not spec:return []
    if spec['method']=='asn-allocation-consensus':return [spec['allocation'],spec['witness']]
    if spec['method']=='allocation-and-routing':return [spec['allocation'],spec['routes']]
    if spec['method']=='domain-ad-consensus':return [*spec['filter-lists'],spec['dns-list']]
    raise rules.Invalid('未知校准方式')


def refresh_reviewed_feed(entry, last, downloaded, *, protected=(), reserved=(), corroborated=(), official=(), tenant_roots=(), observation=None, revision=None, epoch=None, adopt_ads=False, admitted=(),discovery_state=None):
    """Report arbitrary source drift without publishing candidate names or addresses."""
    excluded=set(entry.get('excluded-rules',()))
    allowed=source_policy.publication_kinds(entry)
    permitted=set(entry.get('allowed-shared',()))
    last=outside_domain_scopes(without_protected([
        r for r in last if r not in excluded and r.split(',')[0] in allowed
        and rules.aligned_network(r) and not overbroad(*r.split(',')[:2],permitted)
    ],protected),reserved)
    roots=set(entry.get('exclude-tenant-roots',()))|set(tenant_roots)
    last=outside_tenant_scopes(last,roots,official)
    if not last: raise rules.Invalid('排除业务端点后无法生成非空订阅：'+entry['id'])
    if discovery_state not in (None,'current','review','invalid','unavailable'):
        raise rules.Invalid('自动发现的来源状态无效：'+entry['id'])
    if discovery_state in ('invalid','unavailable'):
        return last,{'state':discovery_state,'discovery-held':True}
    urls=source_policy.rule_feeds(entry)
    spec=entry.get('calibration',{})
    if any(url not in downloaded for url in [*urls,*calibration_urls(spec)]):
        return last,{'state':'unavailable'}
    audit={}
    try:
        now=without_protected(reviewed_input(entry,downloaded,audit=audit,tenant_roots=roots,official=official),protected)
        rules.verify_ip_options(entry,rules.ip_options(now))
    except rules.Invalid:
        return last,{'state':'invalid'}
    outside=dict(audit)
    if admitted:
        last=compact(last+list(admitted));now=compact(now+list(admitted))
    if reserved:
        scoped=outside_domain_scopes(now,reserved)
        if len(now)!=len(scoped): outside['reserved-scopes']=len(now)-len(scoped)
        now=scoped
    if spec:
        if spec['method']=='asn-allocation-consensus':
            try:
                result,stats=calibration.asn_additions(last,now,downloaded[spec['witness']],downloaded[spec['allocation']])
            except (ValueError,rules.Invalid):
                return last,{'state':'invalid'}
            if len(result)-len(last)>max(1,len(last)//20):
                return last,{'state':'review','new-matches':len(result)-len(last),'missing-rules':0,**stats}
            return result,{'state':'current',**stats}
        if spec['method']=='allocation-and-routing':
            try:
                result,stats=calibration.networks(last,now,downloaded[spec['allocation']],downloaded[spec['routes']])
            except (ValueError,rules.Invalid):
                return last,{'state':'invalid'}
            return result,{'state':'current',**stats}
        sources=['\n'.join(downloaded[u] for u in spec['filter-lists']),downloaded[spec['dns-list']]]
        result=calibration.confirmed_ads(now,sources)
        lost=uncovered_count(last,result); gain=uncovered_count(result,last)
        if not result or (not adopt_ads and 20*max(gain,lost)>len(last)):
            return last,{'state':'review','new-matches':gain,'missing-rules':lost}
        return stable_order(result,last),{'state':'current','not-whole-host-consensus':len(now)-len(result),
                                          'admitted-rules':gain,'retired-rules':lost}
    if entry.get('confirm-additions-with'):
        def index(rows):
            exact=set(rows); suffix={r.split(',')[1] for r in exact if r.startswith('DOMAIN-SUFFIX,')}
            def includes(row):
                parts=row.split(',')[1].split('.')
                return row in exact or any('.'.join(parts[i:]) in suffix for i in range(len(parts)))
            return includes
        published=index(last); backed=index(corroborated)
        admitted=[r for r in now if published(r) or backed(r)]
        outside['unconfirmed-domains']=len(now)-len(admitted)
        # A large or empty upstream withdrawal requires review, not a baseline reset.
        lost=uncovered_count(last,admitted); gain=uncovered_count(admitted,last)
        if not admitted or max(lost,gain)>max(1,len(last)//20):
            return last,{'state':'review','new-matches':gain,'missing-rules':lost,**outside}
        return stable_order(admitted,last),{'state':'current',**outside}
    if entry.get('official-hosts'):
        # The vendor assigns a hostname, not the rest of a shared CDN. Retain
        # independently documented coverage even if the community feed lacks it.
        exact=['DOMAIN,'+h for h in sorted(set(official)) if '*' not in h and rules.valid_host(h)]
        extra=[r for r in exact if uncovered_count([r],last)]
        last=stable_order(compact(last+extra),last)
        now=compact(now+exact)
        outside['official-exact-additions']=len(extra)
    if entry.get('reconcile')=='confirmed-withdrawals' and revision is not None:
        last,observed=calibration.withdrawals(last,now,observation or {},revision,epoch)
        if observed:outside['withdrawal-observation']=observed
    added=uncovered_count(now,last)
    removed=uncovered_count(last,now)
    if entry.get('reconcile')=='ad-withdrawals' and removed and removed<=len(last)//20:
        # Trust an upstream withdrawal to narrow blocking, never to expand it.
        # Leave non-domain decisions (IP flags, keywords) for explicit review.
        old_set=set(last)
        old_domains=[r for r in last if r.startswith(('DOMAIN,','DOMAIN-SUFFIX,'))]
        new_domains=[r for r in now if r.startswith(('DOMAIN,','DOMAIN-SUFFIX,'))]
        def index(rows):
            return set(rows),{r.split(',')[1] for r in rows if r.startswith('DOMAIN-SUFFIX,')}
        def present(row,idx):
            exact,suffix=idx; parts=row.split(',')[1].split('.')
            return row in exact or any('.'.join(parts[i:]) in suffix for i in range(len(parts)))
        before,after=index(old_domains),index(new_domains)
        revised=[r for r in last if r not in before[0] or present(r,after)]
        revised+= [r for r in new_domains if r not in old_set and present(r,before)]
        revised=compact(revised)
        if revised and revised!=last:
            last=revised
            added=uncovered_count(now,last)
            removed=uncovered_count(last,now)
    if added or removed:
        return last,{'state':'review','new-matches':added,'missing-rules':removed,**outside}
    return last,{'state':'current',**outside}
