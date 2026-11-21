import copy
import json
from ipaddress import ip_address
import unittest

from loon_rules.generation import pipeline as lib
from loon_rules import rules as maintain


class ReverseDNS(unittest.TestCase):
    def entry(self):
        return {'id':'local','mode':'compiled','ip-match':'per-rule','reverse-dns':True,
                'dns_required':['IP-CIDR,172.16.0.0/12','IP-CIDR6,fc00::/7'],
                'literal_ips':['IP-CIDR,169.254.0.0/16','IP-CIDR6,fe80::/10']}

    def test_non_aligned_prefixes_expand_to_only_their_own_reverse_zones(self):
        rows=maintain.reverse_dns_rules(self.entry())
        expected={'DOMAIN-SUFFIX,'+str(n)+'.172.in-addr.arpa' for n in range(16,32)}
        expected|={'DOMAIN-SUFFIX,c.f.ip6.arpa','DOMAIN-SUFFIX,d.f.ip6.arpa',
                   'DOMAIN-SUFFIX,254.169.in-addr.arpa'}
        expected|={'DOMAIN-SUFFIX,'+digit+'.e.f.ip6.arpa' for digit in '89ab'}
        self.assertEqual(set(rows),expected)

    def test_edges_and_neighbouring_public_addresses_are_not_broadened(self):
        rows=maintain.reverse_dns_rules(self.entry())
        for address in ('172.16.0.0','172.31.255.255','169.254.0.1','fc00::','fdff:ffff::1','fe80::1','febf:ffff::1'):
            self.assertTrue(any(maintain.match_domain(ip_address(address).reverse_pointer,r) for r in rows),address)
        for address in ('172.15.255.255','172.32.0.0','169.253.0.1','fbff::1','fe00::1','fec0::1','1.1.1.1'):
            self.assertFalse(any(maintain.match_domain(ip_address(address).reverse_pointer,r) for r in rows),address)

    def test_changed_networks_recompute_zones_without_a_second_hostname_list(self):
        entry=self.entry();entry['dns_required']=['IP-CIDR,10.20.0.0/16'];entry['literal_ips']=[]
        self.assertEqual(maintain.reverse_dns_rules(entry),['DOMAIN-SUFFIX,20.10.in-addr.arpa'])
        entry['dns_required']=['IP-CIDR6,2001:db8:abcd::/48']
        self.assertEqual(maintain.reverse_dns_rules(entry),['DOMAIN-SUFFIX,d.c.b.a.8.b.d.0.1.0.0.2.ip6.arpa'])

    def test_generation_preserves_ip_parameters_and_the_alternative_inherits_the_zones(self):
        entry=self.entry();rows=lib.compile_entry(entry,{})
        self.assertIn('IP-CIDR,172.16.0.0/12',rows)
        self.assertIn('IP-CIDR,169.254.0.0/16,no-resolve',rows)
        alternative={'id':'local-alt','refine':{'from':'local','literal-ip-copy':True}}
        copied=lib.product_rows(alternative,{'local':rows})
        self.assertEqual({r for r in copied if r.startswith('DOMAIN')},
                         set(maintain.reverse_dns_rules(entry)))
        self.assertTrue(all(r.endswith(',no-resolve') for r in copied if r.startswith('IP-CIDR')))
        audit=lib.maintenance_audit({'local':{**entry,'priority':11}},[])
        self.assertEqual(audit['address-derived'],{'local':23})
        self.assertEqual(audit['fixed-declarations'],{'local':4})

    def test_declarations_require_explicit_ip_purpose_and_cannot_capture_all_reverse_dns(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        for mutation in ({'reverse-dns':'yes'},{'reverse-dns':True,'ip-match':'target-ip'}):
            candidate=copy.deepcopy(cfg)
            entry=next(e for e in candidate['entries'] if e['id']=='local-links-and-addresses')
            entry.update(mutation)
            with self.subTest(mutation=mutation),self.assertRaises(maintain.Invalid):
                lib.validate_declarations(candidate)
        for rule in ('IP-CIDR,0.0.0.0/0','IP-CIDR6,::/0','IP-CIDR,172.16.0.1/12'):
            entry=self.entry();entry['dns_required']=[rule]
            with self.subTest(rule=rule),self.assertRaises(maintain.Invalid):
                maintain.reverse_dns_rules(entry)
