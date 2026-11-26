"""Index a validated rule snapshot for repeated domain, IP and selection checks."""
from fnmatch import translate
from ipaddress import collapse_addresses,ip_address,ip_network
import re
from loon_rules import domains as domain_scope
from loon_rules.rules import Invalid


def merge_cases(config,cases,label):
    critical=dict(config['critical'])
    for host,owners in cases.items():
        if host in critical:
            if not set(owners)<=set(critical[host]):raise Invalid(label+'与固定业务用例的归属不符：'+host)
        else:critical[host]=owners
    return {**config,'critical':critical},len(cases)


class RuleIndex:
    def __init__(self,data,order=None):
        self.order=tuple(data if order is None else order)
        self.bits={key:1<<i for i,key in enumerate(self.order)}
        self.identities={};self._exact={};self._suffix={};self._patterns=[]
        self._networks={False:{4:{},6:{}},True:{4:{},6:{}}}
        self._domains={};self._addresses={};self._scopes={}
        patterns={};networks={}
        for key in self.order:
            bit=self.bits[key];identities=[]
            for row in data.get(key,()):
                kind,value,*flags=row.split(',');value=value.casefold()
                identity=value
                if kind in ('DOMAIN','DOMAIN-SUFFIX'):
                    table=self._exact if kind=='DOMAIN' else self._suffix
                    table[value]=table.get(value,0)|bit
                elif kind in ('DOMAIN-WILDCARD','DOMAIN-KEYWORD'):
                    pair=(kind,value);patterns[pair]=patterns.get(pair,0)|bit
                elif kind in ('IP-CIDR','IP-CIDR6'):
                    if value not in networks:networks[value]=ip_network(value)
                    network=networks[value];identity=str(network)
                    for literal in (False,True):
                        if not literal and 'no-resolve' in flags:continue
                        version=self._networks[literal][network.version]
                        mask,addresses=version.setdefault(network.prefixlen,(int(network.netmask),{}))
                        address=int(network.network_address);addresses[address]=addresses.get(address,0)|bit
                identities.append((kind,identity,tuple(sorted(flags))))
            self.identities[key]=tuple(identities)
        for (kind,value),bits in patterns.items():
            self._patterns.append((kind,value,re.compile(translate(value)) if kind=='DOMAIN-WILDCARD' else None,bits))

    def _matching_domains(self,host):
        if host not in self._domains:
            bits=self._exact.get(host,0);labels=host.split('.')
            for i in range(len(labels)):bits|=self._suffix.get('.'.join(labels[i:]),0)
            for kind,value,pattern,owners in self._patterns:
                if (value in host if kind=='DOMAIN-KEYWORD' else pattern.match(host)):
                    bits|=owners
            self._domains[host]=bits
        return self._domains[host]

    def domain_bits(self,host):
        return self._matching_domains(host.casefold())

    def scope_bits(self,row):
        """Return owners covering the entire domain range, rather than one probe."""
        if row in self._scopes:return self._scopes[row]
        kind,value,*flags=row.split(',');value=value.casefold()
        if flags or kind not in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD'):return 0
        if kind=='DOMAIN':return self.domain_bits(value)
        canonical=kind+','+value
        tail=domain_scope.fixed_tail(value) if kind=='DOMAIN-WILDCARD' else value
        bits=0;labels=tail.split('.')
        for i in range(len(labels)):bits|=self._suffix.get('.'.join(labels[i:]),0)
        descendants=0
        for pattern,host,_,owners in self._patterns:
            if pattern!='DOMAIN-WILDCARD':continue
            parent=pattern+','+host
            if domain_scope.covers(parent,canonical):bits|=owners
            if kind=='DOMAIN-SUFFIX' and domain_scope.covers(parent,'DOMAIN-WILDCARD,*.'+value):descendants|=owners
        if kind=='DOMAIN-SUFFIX':bits|=self._exact.get(value,0)&descendants
        self._scopes[row]=bits
        return bits

    def scope_intersection_bits(self,row):
        """Conservatively include partial intersections; complex globs still need review."""
        kind,value,*flags=row.split(',')
        if flags or kind not in ('DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD'):return 0
        if kind=='DOMAIN':return self.domain_bits(value)
        if not hasattr(self,'_domain_descendants'):
            self._domain_descendants={}
            for table in (self._exact,self._suffix):
                for host,bits in table.items():
                    labels=host.split('.')
                    for i in range(len(labels)):
                        parent='.'.join(labels[i:])
                        self._domain_descendants[parent]=self._domain_descendants.get(parent,0)|bits
        tail=domain_scope.fixed_tail(value) if kind=='DOMAIN-WILDCARD' else value
        bits=self.scope_bits(row)|self._domain_descendants.get(tail,0)
        for pattern,host,_,owners in self._patterns:
            other=domain_scope.fixed_tail(host)
            if pattern=='DOMAIN-KEYWORD' or not tail or not other or tail==other or tail.endswith('.'+other) or other.endswith('.'+tail):
                bits|=owners
        return bits

    def network_intersection_bits(self,target,*,literal):
        """Include any intersecting prefix, respecting each DNS matching mode."""
        if not hasattr(self,'_network_intersections'):self._network_intersections={}
        key=(target,literal)
        if key not in self._network_intersections:
            network=ip_network(target);value=int(network.network_address);mask=int(network.netmask);bits=0
            for prefix,(candidate_mask,addresses) in self._networks[literal][network.version].items():
                if prefix<=network.prefixlen:
                    bits|=addresses.get(value&candidate_mask,0)
                else:
                    for address,owners in addresses.items():
                        if address&mask==value:bits|=owners
            self._network_intersections[key]=bits
        return self._network_intersections[key]

    def network_bits(self,target,*,literal):
        """Return groups covering an entire prefix, including adjacent ranges in one group."""
        if not hasattr(self,'_network_scopes'):
            scopes={False:{4:{},6:{}},True:{4:{},6:{}}}
            for key,identities in self.identities.items():
                for mode in (False,True):
                    networks=[ip_network(value) for kind,value,flags in identities
                              if kind in ('IP-CIDR','IP-CIDR6') and (mode or 'no-resolve' not in flags)]
                    for version in (4,6):
                        for network in collapse_addresses(n for n in networks if n.version==version):
                            mask,addresses=scopes[mode][version].setdefault(network.prefixlen,(int(network.netmask),{}))
                            address=int(network.network_address)
                            addresses[address]=addresses.get(address,0)|self.bits[key]
            self._network_scopes=scopes
        network=ip_network(target);value=int(network.network_address);bits=0
        for prefix,(mask,addresses) in self._network_scopes[literal][network.version].items():
            if prefix<=network.prefixlen:bits|=addresses.get(value&mask,0)
        return bits

    def ip_bits(self,target,*,literal):
        key=(target,literal)
        if key not in self._addresses:
            address=ip_address(target);value=int(address);bits=0
            for mask,networks in self._networks[literal][address.version].values():
                bits|=networks.get(value&mask,0)
            self._addresses[key]=bits
        return self._addresses[key]

    def _first(self,bits,order):
        return next((key for key in order if bits&self.bits.get(key,0)),None)

    def route(self,host,order):
        return self._first(self._matching_domains(host.lower()),order)

    def ip_route(self,target,order,*,literal):
        return self._first(self.ip_bits(target,literal=literal),order)
