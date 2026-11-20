import json
import unittest
import scoped_dns


class ScopedDNS(unittest.TestCase):
    def test_exact_suffix_and_non_dns_selectors_keep_their_scope(self):
        rows = ['DOMAIN,login.example.com','DOMAIN-SUFFIX,service.example.com',
                'DOMAIN-WILDCARD,*buy.example.com','IP-CIDR,192.0.2.0/24,no-resolve']
        self.assertEqual(scoped_dns.names(rows), {'login.example.com','service.example.com','*.service.example.com'})

    def test_shared_dependencies_may_not_be_claimed_by_suffix_or_exact(self):
        for row in ['DOMAIN-SUFFIX,google.com','DOMAIN,accounts.google.com']:
            with self.assertRaises(ValueError):
                scoped_dns.names([row], protected=['accounts.google.com'])

    def test_malformed_or_private_scope_is_never_published(self):
        for value in ['*','bad name.org','123.0.0.1','local','router.local','resolver.arpa','*.internal']:
            with self.assertRaises(ValueError):
                scoped_dns.names(['DOMAIN-SUFFIX,'+value])

    def test_invalid_config_cannot_turn_this_into_plain_dns_or_an_empty_plugin(self):
        for change in [{'resolver':'http://resolver.example/dns-query'},{'groups':[]},
                       {'provider':'name\n[General]'}, {'resolver':'https://user@resolver.example/dns-query'},
                       {'resolver':'https://@resolver.example/dns-query'}]:
            cfg=json.loads((scoped_dns.ROOT/'catalog.json').read_text())
            cfg['scoped-dns'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                scoped_dns.build(cfg)

    def test_installed_artifact_and_required_boundaries(self):
        text=scoped_dns.build()
        self.assertEqual(scoped_dns.OUTPUT.read_text(),text)
        self.assertIn('*.claude.ai = server:',text)
        self.assertIn('gsa.apple.com = server:',text)
        self.assertNotIn('*.apple.com =',text)
        self.assertNotIn('*.googleapis.com =',text)
        self.assertEqual([l for l in text.splitlines() if l.startswith('[')],['[Host]'])
