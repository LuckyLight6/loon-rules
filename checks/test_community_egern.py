"""Egern rule sets use OR fields and apply no_resolve only to IP rules."""
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json

from loon_rules import community
from loon_rules.rules import Invalid


class EgernCommunityInputs(unittest.TestCase):
    def normalize(self,body):
        try:return community.normalize('egern',body)
        except Invalid as error:self.fail('完整的已声明 Egern 集合不应被丢弃：'+str(error))

    def test_complete_or_fields_keep_new_domains_and_ip_resolution_semantics(self):
        body='''no_resolve: true
domain_set:
- login.vendor.example
domain_suffix_set:
  - vendor.example
ip_cidr_set:
  - 8.8.8.0/24
ip_cidr6_set:
  - '2001:4860:4860::/48'
asn_set:
  - AS15169
'''
        for host in ('new-region.example','next-unlisted.example'):
            body=body.replace('domain_set:\n','domain_set:\n- '+host+'\n')
            result=self.normalize(body)
            self.assertIn('DOMAIN,'+host,result['rules'])
            self.assertIn('DOMAIN-SUFFIX,vendor.example',result['rules'])
            self.assertIn('IP-CIDR,8.8.8.0/24,no-resolve',result['rules'])
            self.assertIn('IP-CIDR6,2001:4860:4860::/48,no-resolve',result['rules'])
            self.assertIn('IP-ASN,15169,no-resolve',result['rules'])
            self.assertEqual(result['conditions'],[])
            self.assertNotIn('DOMAIN,'+host+',no-resolve',result['rules'])
        resolving=self.normalize(body.replace('no_resolve: true','no_resolve: false'))
        self.assertIn('IP-CIDR,8.8.8.0/24',resolving['rules'])
        self.assertFalse(any(row.endswith(',no-resolve') for row in resolving['rules']))

    def test_non_domain_predicates_are_preserved_and_not_flattened(self):
        body='''no_resolve: true
domain_set:
  - api.vendor.example
domain_regex_set:
  - '^api\\.[a-z]+\\.example$'
asn_set:
  - 'Telegram Messenger Inc'
geoip_set:
  - US
protocol_set:
  - quic
'''
        result=self.normalize(body)
        self.assertEqual(result['rules'],['DOMAIN,api.vendor.example'])
        self.assertEqual(len(result['conditions']),4)
        self.assertIn('Telegram Messenger Inc',str(result['conditions']))
        self.assertIn('no_resolve',str(result['conditions']))

    def test_unicode_domains_remain_explicit_conditions_without_idna_guessing(self):
        body='domain_set:\n  - api.vendor.example\n  - faß.de\ndomain_suffix_set:\n  - 米.中国\n  - gοoglе.com\n'
        result=self.normalize(body)
        self.assertEqual(result['rules'],['DOMAIN,api.vendor.example'])
        self.assertEqual(len(result['conditions']),3)
        self.assertIn('faß.de',str(result['conditions']))
        self.assertIn('米.中国',str(result['conditions']))
        self.assertIn('gοoglе.com',str(result['conditions']))
        self.assertNotIn('fass.de',str(result))
        with self.assertRaises(Invalid):community.normalize('egern',body.replace('米.中国','米.中国/path'))

    def test_nested_mapping_and_comment_nodes_cannot_become_scalar_conditions(self):
        for field in ('asn_set','ssid_set','domain_regex_set'):
            for value in ('- AS15169','-','organization:','organization:\tAS15169','# omitted','? organization'):
                with self.subTest(field=field,value=value),self.assertRaises(Invalid):
                    community.normalize('egern',field+':\n  - '+value+'\n')
        for value in ('- AS15169','organization: AS15169'):
            result=self.normalize("asn_set:\n  - '"+value+"'\n")
            self.assertEqual(result['conditions'][0]['egern-asn-organization'],value)

    def test_yaml_separation_keeps_unicode_spaces_and_nonbreak_characters(self):
        for character in ('\u00a0','\u0085','\u2028','\u2029'):
            literal=character+'Home'+character+'#Guest'+character
            with self.subTest(character=repr(character)):
                result=self.normalize('ssid_set:\n  - '+literal+'\n')
                self.assertEqual(result['conditions'][0]['egern']['ssid_set'],[literal])
                keyword='tracker'+character+'#Guest'
                result=self.normalize('domain_keyword_set:\n  - '+keyword+'\n')
                self.assertEqual(result['rules'],[])
                self.assertEqual(result['conditions'][0]['egern']['domain_keyword_set'],[keyword])
        for suffix in ("'Home'\u00a0",'"Home"\u00a0'):
            with self.assertRaises(Invalid):community.normalize('egern','ssid_set:\n  - '+suffix+'\n')
        with self.assertRaises(Invalid):
            community.normalize('egern','no_resolve:\u00a0true\ndomain_set:\n  - api.vendor.example\n')
        self.assertEqual(self.normalize('ssid_set:\n  -\tHome # real comment\n')['conditions'][0]['egern']['ssid_set'],['Home'])

    def test_unknown_scalar_structure_retains_the_previous_complete_observation(self):
        from loon_rules.community_review import run
        with TemporaryDirectory() as temporary,redirect_stdout(StringIO()):
            root=Path(temporary)
            for folder in ('config','rules/loon','data'):(root/folder).mkdir(parents=True)
            source={'id':'public-service','repository':'public/source','ref':'release','path':'service.yaml','format':'egern','products':['service']}
            (root/'config/community-sources.json').write_text(json.dumps({'schema-version':1,'inputs':[source],'queries':[]}))
            entry={'id':'service','mode':'compiled','priority':10,'section':'products','description':'产品',
                   'boundary':'专用服务','sources':['https://vendor.example/'],'include':['DOMAIN-SUFFIX,service.example']}
            config={'schema-version':2,'sections':[{'id':'products','title':'产品'}],'entries':[entry],'critical':{},'shared-negatives':[]}
            (root/'config/catalog.json').write_text(json.dumps(config))
            (root/'rules/loon/010-service.lsr').write_text('DOMAIN-SUFFIX,service.example\n')
            revision=['a'*40];body=[b'domain_set:\n  - api.service.example\n']
            def resolve(*args):return {'revision':revision[0],'committed-at':'2026-11-27T00:00:00Z'}
            with patch('loon_rules.community_review.resolve',side_effect=resolve),patch('loon_rules.community_review.download',side_effect=lambda url:body[0]):
                self.assertEqual(run(root,search=False)['inputs-normalized'],1)
                before=json.loads((root/'data/community-state.json').read_text())['inputs']['public-service']
                revision[0]='b'*40;body[0]+=b'asn_set:\n  - - AS15169\n'
                result=run(root,search=False)
                self.assertEqual(result['inputs-held'],1)
                self.assertEqual(json.loads((root/'data/community-state.json').read_text())['inputs']['public-service'],before)

    def test_unknown_duplicate_nested_or_wrong_family_inputs_stop_complete_reading(self):
        valid='domain_set:\n  - api.vendor.example\n'
        invalid=[
            valid+'domain_set:\n  - second.example\n',
            valid+'unknown_set:\n  - hidden.example\n',
            valid+'and_set:\n  - domain_set:\n      - private.example\n',
            valid+'ip_cidr_set:\n  - 2001:4860:4860::/48\n',
            valid+'ip_cidr6_set:\n  - 8.8.8.0/24\n',
            valid+'no_resolve: maybe\n',
            valid+'domain_suffix_set:\n',
            valid+'domain_suffix_set: [vendor.example]\n',
            valid+'domain_suffix_set:\n  - &alias vendor.example\n',
            valid+'domain_suffix_set:\n  - *alias\n',
            valid+'domain_suffix_set:\n  - !!str vendor.example\n',
            'domain_set:\n  - foo: bar\n',
        ]
        for body in invalid:
            with self.subTest(body=body),self.assertRaises(Invalid):
                community.normalize('egern',body)


if __name__=='__main__':unittest.main()
