from itertools import permutations
import unittest

from loon_rules.generation import pipeline as lib


class MatchingIndex(unittest.TestCase):
    def fixture(self):
        return {
            'exact':['DOMAIN,API.vendor.example','IP-CIDR,198.51.100.0/24,no-resolve',
                     'IP-CIDR6,2001:db8:1::/48,no-resolve'],
            'suffix':['DOMAIN-SUFFIX,vendor.example','IP-CIDR,198.51.0.0/16',
                      'IP-CIDR6,2001:db8::/32'],
            'patterns':['DOMAIN-WILDCARD,p[0-9][0-9]-api.vendor.example',
                        'DOMAIN-WILDCARD,*.other.example','DOMAIN-KEYWORD,login'],
            'fallback':['DOMAIN-KEYWORD,example','DOMAIN-SUFFIX,com','GEOIP,CN',
                        'IP-ASN,12345,no-resolve','PROCESS-NAME,client']}

    def test_domain_results_match_the_existing_interpreter_for_all_priority_orders(self):
        from loon_rules.matching import RuleIndex
        data=self.fixture();index=RuleIndex(data)
        hosts=['api.vendor.example','API.VENDOR.EXAMPLE','vendor.example','login.other.example',
               'p01-api.vendor.example','p999-api.vendor.example','cdn.other.example',
               'other.example','a.b.other.example','unrelated.com','unrelated.net']
        for order in permutations(data):
            for host in hosts:
                self.assertEqual(index.route(host,order),lib.ordered_route(host,order,data),(order,host))

    def test_ip_results_preserve_literal_and_dns_matching_modes_across_priority_orders(self):
        from loon_rules.matching import RuleIndex
        data=self.fixture();index=RuleIndex(data)
        for order in permutations(data):
            for literal in (False,True):
                for address in ('198.51.100.1','198.51.101.1','203.0.113.1','2001:db8:1::1','2001:db8:2::1','::1'):
                    self.assertEqual(index.ip_route(address,order,literal=literal),
                        lib.ordered_ip_route(address,order,data,literal=literal),(order,address,literal))

    def test_selected_bits_cover_every_matching_group_not_just_the_first(self):
        from loon_rules.matching import RuleIndex
        data=self.fixture();index=RuleIndex(data)
        for host in ('api.vendor.example','p09-api.vendor.example','login.other.example','other.example'):
            expected=sum(index.bits[key] for key,rows in data.items() if any(lib.rules.match_domain(host,r) for r in rows))
            self.assertEqual(index.domain_bits(host),expected)

    def test_snapshot_does_not_cache_mutable_inputs_or_reorder_duplicate_selections(self):
        from loon_rules.matching import RuleIndex
        data=self.fixture();index=RuleIndex(data)
        data['exact'].append('DOMAIN,new.other.example')
        order=['exact','patterns','exact']
        self.assertEqual(index.route('new.other.example',order),'patterns')
        self.assertEqual(RuleIndex(data).route('new.other.example',order),'exact')
        self.assertIsNone(index.route('api.vendor.example',['unknown']))
        self.assertIsNone(index.route('api.vendor.example',[]))

    def test_scope_bits_require_whole_range_coverage_and_support_exact_plus_wildcard_unions(self):
        from loon_rules.matching import RuleIndex
        data={'whole':['DOMAIN,service.example','DOMAIN-WILDCARD,*.service.example'],
              'descendants':['DOMAIN-WILDCARD,*.service.example'],
              'one':['DOMAIN,api.service.example'],
              'parent':['DOMAIN-SUFFIX,example']}
        index=RuleIndex(data)
        self.assertEqual(index.scope_bits('DOMAIN-SUFFIX,service.example'),index.bits['whole']|index.bits['parent'])
        self.assertEqual(index.scope_bits('DOMAIN,api.service.example'),sum(index.bits.values()))
        self.assertEqual(index.scope_bits('DOMAIN-WILDCARD,p??.service.example'),
                         index.bits['whole']|index.bits['descendants']|index.bits['parent'])
        self.assertEqual(index.scope_bits('DOMAIN-SUFFIX,api.service.example'),
                         index.bits['whole']|index.bits['descendants']|index.bits['parent'])
        split=RuleIndex({'apex':['DOMAIN,service.example'],'children':['DOMAIN-WILDCARD,*.service.example']})
        self.assertEqual(split.scope_bits('DOMAIN-SUFFIX,service.example'),0)

    def test_network_scope_bits_cover_whole_prefixes_and_preserve_dns_modes(self):
        from loon_rules.matching import RuleIndex
        index=RuleIndex({'one':['IP-CIDR,198.51.100.0/25,no-resolve','IP-CIDR,198.51.100.128/25,no-resolve'],
            'left':['IP-CIDR,203.0.113.0/25'], 'right':['IP-CIDR,203.0.113.128/25'],
            'six':['IP-CIDR6,2001:db8::/33','IP-CIDR6,2001:db8:8000::/33']})
        self.assertEqual(index.network_bits('198.51.100.0/24',literal=True),index.bits['one'])
        self.assertEqual(index.network_bits('198.51.100.0/24',literal=False),0)
        self.assertEqual(index.network_bits('203.0.113.0/24',literal=True),0)
        self.assertEqual(index.network_bits('203.0.113.0/25',literal=False),index.bits['left'])
        self.assertEqual(index.network_bits('2001:db8::/32',literal=False),index.bits['six'])
