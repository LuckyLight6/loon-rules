"""Whole public network metadata is validated before selecting owned namespaces."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class PublicNetworkMetadata(PublicSourceExamples):
    def recipe(self, all_patterns=False):
        recipe = {'format': 'public-network-metadata',
                  'source': 'https://api.product.example/v1/public/meta',
                  'brand-label': 'product',
                  'shared-patterns': ['*.cloud.example', 'verify.shared.example']}
        if all_patterns:
            recipe['all-patterns'] = True
        return recipe

    def document(self):
        return {'egressIps': [{'ip': '8.8.8.8', 'ipVersion': 'IPv4'},
                              {'ip': '2606:4700::1111', 'ipVersion': 'IPv6'}],
                'domains': [{'pattern': '*.product.example',
                             'details': [{'domain': 'api.product.example', 'purpose': 'Global service'},
                                         {'domain': 'product.example', 'purpose': 'Website'}]},
                            {'pattern': '*.product.sh'},
                            {'pattern': '*.cloud.example',
                             'details': [{'domain': '*.captcha.cloud.example', 'purpose': 'Login captcha'}]},
                            {'pattern': 'verify.shared.example'}]}

    def read(self, document=None, recipe=None):
        try:
            return extract_rows(recipe or self.recipe(), json.dumps(document or self.document()))
        except Invalid as error:
            self.fail('完整公开网络元数据应被读取：' + str(error))

    def test_coarse_patterns_drive_owned_output_without_promoting_optional_details_or_egress(self):
        expected = {'DOMAIN-WILDCARD,*.product.example', 'DOMAIN-WILDCARD,*.product.sh'}
        self.assertEqual(self.read(), expected)
        document = self.document()
        document['domains'][0].pop('details')
        self.assertEqual(self.read(document), expected)
        self.assertEqual(self.read(recipe=self.recipe(True)), expected | {
            'DOMAIN-WILDCARD,*.cloud.example', 'DOMAIN,verify.shared.example'})

    def test_new_unseeded_owned_namespace_and_host_are_discovered_from_complete_patterns(self):
        document = self.document()
        document['domains'] += [{'pattern': '*.product.net'}, {'pattern': 'region.product.org'}]
        self.assertEqual(self.read(document), {
            'DOMAIN-WILDCARD,*.product.example', 'DOMAIN-WILDCARD,*.product.sh',
            'DOMAIN-WILDCARD,*.product.net', 'DOMAIN,region.product.org'})

    def test_every_unselected_shared_record_and_optional_detail_is_validated(self):
        changes = [
            {'pattern': '*.unknown.example'},
            {'pattern': '*.cloud.example', 'newField': ['hidden.example']},
            {'pattern': '*.cloud.example', 'details': 'not-an-array'},
            {'pattern': '*.cloud.example', 'details': []},
            {'pattern': '*.cloud.example', 'details': [{'domain': 'outside.example'}]},
            {'pattern': '*.cloud.example', 'details': [{'domain': 'host.cloud.example', 'purpose': False}]},
            {'pattern': '*.cloud.example', 'details': [{'domain': 'host.cloud.example', 'purpose': ' '} ]},
            {'pattern': '*.cloud.example', 'details': [{'domain': 'host.cloud.example', 'network': '8.8.8.8'}]},
            {'pattern': '*.cloud.example', 'details': [{'domain': 'host.cloud.example'}, {'domain': 'host.cloud.example'}]},
        ]
        for replacement in changes:
            document = self.document()
            document['domains'][2] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(Invalid):
                extract_rows(self.recipe(), json.dumps(document))

    def test_missing_declared_shared_scope_stops_a_filtered_update(self):
        document = self.document()
        document['domains'].pop()
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), json.dumps(document))

    def test_owned_scope_conflicting_with_a_declared_shared_host_is_not_silently_removed(self):
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), json.dumps(self.document()), shared_hosts=['api.product.sh'])

    def test_exact_coarse_scope_cannot_hide_a_wider_detail(self):
        for detail in ('other.shared.example', '*.verify.shared.example'):
            document = self.document()
            document['domains'][-1]['details'] = [{'domain': detail}]
            with self.subTest(detail=detail), self.assertRaises(Invalid):
                extract_rows(self.recipe(), json.dumps(document))

    def test_egress_addresses_validate_both_families_without_becoming_destination_rules(self):
        bad = [{'ip': '8.8.8.8', 'ipVersion': 'IPv6'}, {'ip': '10.0.0.1', 'ipVersion': 'IPv4'},
               {'ip': '8.8.8.0/24', 'ipVersion': 'IPv4'}, {'ip': False, 'ipVersion': 'IPv4'},
               {'ip': '2606:4700::1111', 'ipVersion': 'IPv4'},
               {'ip': '2606:4700::1111', 'ipVersion': 'Other'},
               {'ip': '8.8.8.8', 'ipVersion': 'IPv4', 'direction': 'ingress'}]
        for replacement in bad:
            document = self.document()
            document['egressIps'][0] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(Invalid):
                extract_rows(self.recipe(), json.dumps(document))
        document = self.document()
        document['egressIps'].append(deepcopy(document['egressIps'][0]))
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), json.dumps(document))

    def test_multicast_addresses_are_not_valid_public_service_egress(self):
        for address, family in (('224.0.0.1', 'IPv4'), ('ff02::1', 'IPv6')):
            document = self.document()
            document['egressIps'][0] = {'ip': address, 'ipVersion': family}
            with self.subTest(address=address), self.assertRaises(Invalid):
                extract_rows(self.recipe(), json.dumps(document))

    def test_incomplete_or_ambiguous_response_and_noncanonical_patterns_stop_update(self):
        for field in ('domains', 'egressIps'):
            for replacement in (None, [], {}, False):
                document = self.document()
                document[field] = replacement
                with self.subTest(field=field, value=replacement), self.assertRaises(Invalid):
                    extract_rows(self.recipe(), json.dumps(document))
        for pattern in ('*.com', 'https://product.example', '*product.example', 'api?.product.example',
                        '*.product.example.', ' *.product.example', '*.PRODUCT.example'):
            document = self.document()
            document['domains'][0]['pattern'] = pattern
            with self.subTest(pattern=pattern), self.assertRaises(Invalid):
                extract_rows(self.recipe(), json.dumps(document))
        document = self.document()
        document['domains'].append(deepcopy(document['domains'][0]))
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), json.dumps(document))
        for body in (json.dumps({**self.document(), 'next': '/page2'}),
                     json.dumps(self.document())[:-1] + ',"domains": []}',
                     '{"domains": [], "egressIps": NaN}'):
            with self.subTest(body=body), self.assertRaises(Invalid):
                extract_rows(self.recipe(), body)

    def test_recipe_identity_shared_declarations_and_options_cannot_be_ambiguous(self):
        changes = [{'brand-label': 'other'}, {'brand-label': False},
                   {'source': 'https://product.example.evil.org/v1/public/meta'},
                   {'source': 'https://api.product.example/v1/public/meta?account=1'},
                   {'shared-patterns': ['*.product.example']},
                   {'shared-patterns': ['*.cloud.example', '*.cloud.example']},
                   {'shared-patterns': False}, {'all-patterns': 'yes'}, {'all-patterns': True, 'unknown': True}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(Invalid):
                extract_rows({**self.recipe(), **change}, json.dumps(self.document()))


class PublicNetworkMetadataDeclarations(unittest.TestCase):
    def catalog(self):
        config = json.loads((Path(__file__).resolve().parents[1] / 'config/catalog.json').read_text())
        entry = next(item for item in config['entries'] if item['id'] == 'qoder-international')
        source = 'https://api.qoder.com/v1/public/meta'
        recipe = {'source': source, 'format': 'public-network-metadata',
                  'brand-label': 'qoder', 'shared-patterns': ['*.cloud.example']}
        if source not in entry['sources']:
            entry['sources'].append(source)
        entry['extract'] = [recipe]
        config['source-inventories'] = [item for item in config['source-inventories'] if item['source'] != source]
        whole = {key: value for key, value in recipe.items() if key != 'source'}
        whole['all-patterns'] = True
        return config, entry, {'id': 'complete-public-network', 'source': source,
                               'recipe': whole, 'owners': [entry['id']]}

    def test_owned_selection_requires_independent_unfiltered_matching_inventory(self):
        from loon_rules.generation.declarations import validate_declarations
        config, entry, inventory = self.catalog()
        with self.assertRaises(Invalid):
            validate_declarations(config)
        config['source-inventories'].append(inventory)
        validate_declarations(config)
        for change in ({'all-patterns': False}, {'shared-patterns': []}, {'brand-label': 'other'}):
            changed = deepcopy(config)
            changed['source-inventories'][-1]['recipe'].update(change)
            with self.subTest(change=change), self.assertRaises(Invalid):
                validate_declarations(changed)
        entry['extract'][0]['all-patterns'] = True
        with self.assertRaises(Invalid):
            validate_declarations(config)

    def test_discovery_cannot_bypass_the_complete_metadata_inventory_gate(self):
        from loon_rules.generation.declarations import validate_declarations
        config, entry, inventory = self.catalog()
        recipe = entry['extract'][0]
        entry['extract'] = [{'source': entry['sources'][0], 'format': 'domain-scope-list'}]
        entry['discovery'] = {'inputs': [{'source': recipe['source'], 'family': 'official-qoder',
                                        'authority': True, 'recipe': recipe}]}
        with self.assertRaises(Invalid):
            validate_declarations(config)
        config['source-inventories'].append(inventory)
        with self.assertRaises(Invalid):
            validate_declarations(config)

    def test_nested_json_document_cannot_enable_full_shared_metadata_in_a_product(self):
        from loon_rules.generation.declarations import validate_declarations
        config, entry, inventory = self.catalog()
        recipe = deepcopy(entry['extract'][0])
        recipe.pop('source')
        recipe['all-patterns'] = True
        entry['extract'] = [{'source': inventory['source'], 'format': 'json-document',
                             'body-path': ['payload'], 'document': recipe}]
        config['source-inventories'].append(inventory)
        with self.assertRaises(Invalid):
            validate_declarations(config)
