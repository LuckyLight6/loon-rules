import unittest
from loon_rules.generation import calibration as cal
from loon_rules.rules import Invalid

class Calibration(unittest.TestCase):
    def test_new_address_space_needs_both_evidence_sources(self):
        old=['IP-CIDR,8.2.0.0/16','IP-CIDR6,2400:1000::/32']
        new=old+['IP-CIDR,8.3.0.0/24']
        reg='apnic|CN|ipv4|8.2.0.0|65536|20200101|allocated\napnic|CN|ipv4|8.3.0.0|256|20200101|allocated\napnic|CN|ipv6|2400:1000::|32|20200101|allocated'
        got,stats=cal.networks(old,new,reg,'8.2.0.0/16\n8.3.0.0/25\n2400:1000::/32')
        self.assertIn('IP-CIDR,8.3.0.0/25',got)
        self.assertNotIn('IP-CIDR,8.3.0.128/25',got)
        self.assertGreater(stats['unconfirmed-prefixes'],0)
        with self.assertRaises(Invalid): cal.networks(old,['IP-CIDR,8.3.0.0/24'],reg,'8.3.0.0/24')

    def test_existing_address_space_is_checked_again_and_split_at_the_evidence_boundary(self):
        old=['IP-CIDR,8.2.0.0/16','IP-CIDR6,2400:1000::/32']
        reg='apnic|CN|ipv4|8.2.0.0|65536|20200101|allocated\napnic|CN|ipv6|2400:1000::|32|20200101|allocated'
        from ipaddress import ip_network
        routes='\n'.join(str(n) for n in ip_network('8.2.0.0/16').address_exclude(ip_network('8.2.255.0/24')))+'\n2400:1000::/32'
        out,stats=cal.networks(old,old,reg,routes)
        self.assertTrue(all(not ip_network(r.split(',')[1]).overlaps(ip_network('8.2.255.0/24'))
                            for r in out if r.startswith('IP-CIDR,')))
        self.assertGreater(stats['retired-prefixes'],0)
        self.assertGreater(stats['unconfirmed-prefixes'],0)
        with self.assertRaises(Invalid):cal.networks(old,old,reg,'8.2.0.0/24\n2400:1000::/32')
    def test_dns_block_requires_whole_host_evidence_and_respects_exceptions(self):
        sources=['||ads.example^\n||shop.example^$script\n||child.test.example^\n||skip.example^',
                 '||ads.example^\n||shop.example^\n||child.test.example^\n||skip.example^\n@@||auth.ads.example/sso$document']
        scopes=['DOMAIN-SUFFIX,'+h for h in ('ads.example','shop.example','test.example','skip.example')]
        self.assertEqual(cal.confirmed_ads(scopes,sources),['DOMAIN-SUFFIX,skip.example'])

    def test_domestic_confirmation_does_not_promote_a_shared_parent(self):
        from loon_rules.generation import pipeline as lib
        e={'id':'secondary','sources':['feed'],'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[],
           'confirm-additions-with':['local-products']}
        old=['DOMAIN,known.example']
        raw=['DOMAIN-SUFFIX,mixed.example','DOMAIN,new.product.example','DOMAIN,unrelated.example']
        got,stats=lib.refresh_reviewed_feed(e,old,{'feed':'\n'.join(old+raw)},
                corroborated=['DOMAIN,cn.mixed.example','DOMAIN-SUFFIX,product.example'])
        self.assertEqual(set(got),{*old,'DOMAIN,new.product.example'})
        self.assertEqual(stats['unconfirmed-domains'],2)
        self.assertEqual(stats['state'],'current')
