import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from loon_rules.plugins import scoped_dns


class ScopedDNS(unittest.TestCase):
    def test_four_digit_catalog_reads_padded_rule_files_without_full_schema(self):
        cfg={'priority-width':4,'entries':[{'id':'service','priority':110}],
             'shared-negatives':[],
             'scoped-dns':{'provider':'Cloudflare','resolver':'https://1.1.1.1/dns-query',
                           'groups':['service']}}
        with TemporaryDirectory() as tmp,patch.object(scoped_dns,'ROOT',Path(tmp)):
            folder=Path(tmp)/'rules' / 'loon';folder.mkdir(parents=True)
            (folder/'0110-service.lsr').write_text('DOMAIN,api.vendor.example\n')
            result=scoped_dns.build(cfg)
            self.assertIn('来源规则组 0110\n',result)
            self.assertIn('api.vendor.example = server:https://1.1.1.1/dns-query',result)

    def test_different_public_services_can_use_distinct_encrypted_resolvers(self):
        cfg={'entries':[{'id':'overseas','priority':101},{'id':'mainland','priority':501}],
             'shared-negatives':[],
             'scoped-dns':{'routes':[
                 {'label':'海外业务','provider':'Cloudflare','resolver':'https://1.1.1.1/dns-query','groups':['overseas']},
                 {'label':'国内业务','provider':'国内解析器','resolver':'https://doh.pub/dns-query','groups':['mainland']}]}}
        with TemporaryDirectory() as tmp,patch.object(scoped_dns,'ROOT',Path(tmp)):
            folder=Path(tmp)/'rules' / 'loon';folder.mkdir(parents=True)
            (folder/'101-overseas.lsr').write_text('DOMAIN-SUFFIX,foreign.example.com\n')
            (folder/'501-mainland.lsr').write_text('DOMAIN,domestic.example.com\n')
            result=scoped_dns.build(cfg)
            self.assertIn('*.foreign.example.com = server:https://1.1.1.1/dns-query',result)
            self.assertIn('domestic.example.com = server:https://doh.pub/dns-query',result)
            self.assertEqual([line for line in result.splitlines() if line.startswith('[')],['[Host]'])
            (folder/'501-mainland.lsr').write_text('DOMAIN,login.foreign.example.com\n')
            with self.assertRaisesRegex(ValueError,'conflicting resolvers'):scoped_dns.build(cfg)

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
            cfg=json.loads((scoped_dns.ROOT/'config/catalog.json').read_text())
            spec=cfg['scoped-dns']
            cfg['scoped-dns']=dict(spec['routes'][0] if 'routes' in spec else spec)
            cfg['scoped-dns'].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                scoped_dns.build(cfg)

    def test_original_single_resolver_settings_still_work(self):
        cfg=json.loads((scoped_dns.ROOT/'config/catalog.json').read_text())
        spec=cfg['scoped-dns']
        cfg['scoped-dns']=dict(spec['routes'][0] if 'routes' in spec else spec)
        result=scoped_dns.build(cfg)
        self.assertIn('*.claude.ai = server:'+cfg['scoped-dns']['resolver'],result)

    def test_installed_artifact_and_required_boundaries(self):
        text=scoped_dns.build()
        self.assertEqual(scoped_dns.OUTPUT.read_text(),text)
        self.assertIn('*.claude.ai = server:',text)
        self.assertIn('gsa.apple.com = server:',text)
        self.assertNotIn('*.apple.com =',text)
        self.assertNotIn('*.googleapis.com =',text)
        self.assertNotIn('challenges.cloudflare.com =',text)
        self.assertNotIn('humb.apple.com = server:https://1.1.1.1',text)
        self.assertEqual([l for l in text.splitlines() if l.startswith('[')],['[Host]'])
