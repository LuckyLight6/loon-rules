"""Product region variables must follow both official purpose lists and SDK metadata."""
from copy import deepcopy
import json
import unittest

from loon_rules.rules import Invalid


class AWSCodingRegions(unittest.TestCase):
    def spec(self):
        return {'profile-source': 'https://docs.vendor.example/profiles.md',
                'profile-heading': 'Q profiles',
                'sso-source': 'https://docs.vendor.example/regions.md',
                'sso-heading': 'Default regions',
                'sdk-source': 'https://sdk.vendor.example/endpoints.json',
                'partition': 'aws', 'dns-suffix': 'amazonaws.com'}

    def documents(self):
        sdk = {'version': 3, 'partitions': [
            {'partition': 'aws', 'dnsSuffix': 'amazonaws.com', 'regions': {
                'us-east-1': {'description': 'US East (N. Virginia)'},
                'eu-central-1': {'description': 'Europe (Frankfurt)'},
                'sa-east-1': {'description': 'South America (Sao Paulo)'},
                'ap-east-1': {'description': 'Asia Pacific (Hong Kong)'}}},
            {'partition': 'aws-cn', 'dnsSuffix': 'amazonaws.com.cn',
             'regions': {'cn-north-1': {'description': 'China (Beijing)'}}}]}
        return {self.spec()['profile-source']: '# Product regions\n\n### Q profiles\n\n'
                '+ US East (N. Virginia)\n+ Europe (Frankfurt)\n\n### Other uses\n+ Asia Pacific (Hong Kong)\n',
                self.spec()['sso-source']: '# Product availability\n\n## Default regions\n\n'
                '+ US East (N. Virginia)\n+ Europe (Frankfurt)\n+ South America (São Paulo)\n\n'
                '## Opt-in regions\n+ Asia Pacific (Hong Kong)\n',
                self.spec()['sdk-source']: json.dumps(sdk)}

    def read(self, documents=None, spec=None):
        try:
            from loon_rules.sources import aws_coding
        except ImportError:
            self.fail('官方编程服务地区变量读取尚未实现')
        return aws_coding.region_bindings(spec or self.spec(), documents or self.documents())

    def test_profile_and_sso_use_distinct_complete_lists_and_exclude_opt_in_regions(self):
        result = self.read()
        self.assertEqual(result['profile-regions'], ['eu-central-1', 'us-east-1'])
        self.assertEqual(result['sso-regions'], ['eu-central-1', 'sa-east-1', 'us-east-1'])
        self.assertEqual(result['dns-suffix'], 'amazonaws.com')

    def test_new_region_is_discovered_only_when_both_official_sources_describe_it(self):
        documents = self.documents()
        documents[self.spec()['profile-source']] = documents[self.spec()['profile-source']].replace(
            '### Other uses', '+ Australia (New Region)\n\n### Other uses')
        with self.assertRaises(Invalid):
            self.read(documents)
        sdk = json.loads(documents[self.spec()['sdk-source']])
        sdk['partitions'][0]['regions']['ap-southeast-9'] = {'description': 'Australia (New Region)'}
        documents[self.spec()['sdk-source']] = json.dumps(sdk)
        self.assertEqual(self.read(documents)['profile-regions'], ['ap-southeast-9', 'eu-central-1', 'us-east-1'])
        self.assertNotIn('ap-southeast-9', self.read(documents)['sso-regions'])

    def test_empty_duplicate_missing_or_mixed_section_lists_stop_region_materialization(self):
        base = self.documents()
        source = self.spec()['profile-source']
        for body in (base[source].replace('### Q profiles', '### Unknown purpose'),
                     base[source].replace('### Other uses', '### Q profiles'),
                     base[source].replace('+ US East (N. Virginia)\n+ Europe (Frankfurt)', ''),
                     base[source].replace('+ Europe (Frankfurt)', '+ Europe (Frankfurt)\n+ Europe (Frankfurt)'),
                     base[source].replace('+ Europe (Frankfurt)', '+ 8.8.8.8'),
                     base[source].replace('+ Europe (Frankfurt)', '+ Unpublished region')):
            with self.subTest(body=body), self.assertRaises(Invalid):
                self.read({**base, source: body})

    def test_all_selected_partition_metadata_is_validated_before_picking_product_regions(self):
        documents = self.documents()
        sdk = json.loads(documents[self.spec()['sdk-source']])
        changes = []
        value = deepcopy(sdk); value['version'] = True; changes.append(value)
        value = deepcopy(sdk); value['partitions'][0]['dnsSuffix'] = 'evil.example'; changes.append(value)
        value = deepcopy(sdk); value['partitions'].append(deepcopy(value['partitions'][0])); changes.append(value)
        value = deepcopy(sdk); value['partitions'][0]['regions']['ap-east-1']['hostname'] = 'hidden.example'; changes.append(value)
        value = deepcopy(sdk); value['partitions'][0]['regions']['ap-east-1']['description'] = False; changes.append(value)
        value = deepcopy(sdk); value['partitions'][0]['regions']['ap-east-1']['description'] = 'Europe (Frankfurt)'; changes.append(value)
        value = deepcopy(sdk); value['partitions'][0]['regions']['bad region'] = {'description': 'Other place'}; changes.append(value)
        for value in changes:
            with self.subTest(value=value), self.assertRaises(Invalid):
                self.read({**documents, self.spec()['sdk-source']: json.dumps(value)})

    def test_duplicate_json_keys_and_unsupported_region_context_declarations_stop_the_source(self):
        documents = self.documents()
        body = documents[self.spec()['sdk-source']][:-1] + ', "version":3}'
        with self.assertRaises(Invalid):
            self.read({**documents, self.spec()['sdk-source']: body})
        for change in ({'partition': False}, {'dns-suffix': '*.amazonaws.com'},
                       {'profile-heading': ''}, {'profile-source': 'https://user@docs.vendor.example/profiles.md'}):
            with self.subTest(change=change), self.assertRaises(Invalid):
                self.read(spec={**self.spec(), **change})
