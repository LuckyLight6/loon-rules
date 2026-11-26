"""Read complete public security-program assets before splitting their products."""
import copy
import json

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class SecurityAssetSources(PublicSourceExamples):
    def test_reader_is_supported(self):
        from loon_rules.sources.formats import READERS
        self.assertIn('security-program-domains', READERS)

    def test_reader_can_be_imported_before_the_format_dispatcher(self):
        import subprocess
        import sys
        result = subprocess.run([sys.executable, '-B', '-c',
                                 'from loon_rules.sources import security_programs; print(security_programs.FORMAT)'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'security-program-domains')

    def recipe(self):
        return {
            'format': 'security-program-domains',
            'program': {'handle': 'vendor', 'name': 'Vendor', 'url': 'https://hackerone.com/vendor'},
            'assets': [{'type': 'OTHER', 'label': 'Audio product', 'read': 'fenced-domains',
                        'purpose': 'These targets are in scope:',
                        'excluded-purposes': {'These targets are NOT in scope:': '测试范围的否定列表不当作正面用途'}}],
        }

    def asset(self, kind, identifier, instruction='', *, eligible=True):
        return {'asset_type': kind, 'asset_identifier': identifier, 'instruction': instruction,
                'eligible_for_submission': eligible, 'eligible_for_bounty': False}

    def document(self):
        return [dict(self.recipe()['program'], targets={
            'in_scope': [
                self.asset('OTHER', 'Audio product',
                           'These targets are in scope:\n\n```\naudio.example\ncdn.tenant.example\n```'),
                self.asset('SOURCE_CODE', 'https://github.com/vendor/audio'),
            ],
            'out_of_scope': [self.asset('URL', 'https://unrelated.example/', eligible=False)],
        })]

    def whole(self):
        return {**self.recipe(), 'complete': True,
                'non-network-types': {'SOURCE_CODE': '源码地址不是该产品服务器或进程标识'}}

    def test_purpose_lists_follow_unprefilled_roots_and_keep_tenants_exact(self):
        document = self.document()
        self.assertEqual(extract_rows(self.recipe(), json.dumps(document)), {
            'DOMAIN-SUFFIX,audio.example', 'DOMAIN,cdn.tenant.example'})
        document[0]['targets']['in_scope'][0]['instruction'] += '\n\nThese targets are NOT in scope:\n```\nno.example\n```'
        self.assertEqual(extract_rows(self.recipe(), json.dumps(document)), {
            'DOMAIN-SUFFIX,audio.example', 'DOMAIN,cdn.tenant.example'})
        document[0]['targets']['in_scope'][0]['instruction'] = (
            'These targets are in scope:\n\n~~~\naudio.example\nbrand-new.other-provider.example\n')
        self.assertIn('DOMAIN,brand-new.other-provider.example',
                      extract_rows(self.recipe(), json.dumps(document)))

    def test_purpose_can_end_a_paragraph_that_also_describes_the_product(self):
        document = self.document()
        document[0]['targets']['in_scope'][0]['instruction'] = (
            'These are the product websites.\n[Non-core asset]\nThese targets are in scope:\n\n```\naudio.example\n```')
        self.assertEqual(extract_rows(self.recipe(), json.dumps(document)), {'DOMAIN-SUFFIX,audio.example'})

    def test_whole_program_must_account_for_every_asset_not_only_selected_domains(self):
        document = self.document()
        self.assertEqual(extract_rows(self.whole(), json.dumps(document)),
                         extract_rows(self.recipe(), json.dumps(document)))
        for extra in (self.asset('URL', 'https://another-product.example/'),
                      self.asset('IP_ADDRESS', '8.8.8.0/24'),
                      self.asset('OTHER', 'New product', '```\nnew.example\n```')):
            with self.subTest(extra=extra), self.assertRaises(Invalid):
                extract_rows(self.whole(), json.dumps([dict(document[0], targets={
                    **document[0]['targets'], 'in_scope': document[0]['targets']['in_scope'] + [extra]})]))

    def test_wrong_identity_type_negated_purpose_and_incomplete_json_are_rejected(self):
        for changed in ('handle', 'name', 'url', 'type', 'negative', 'missing', 'duplicate', 'truncated'):
            document = self.document()
            if changed in ('handle', 'name', 'url'): document[0][changed] += '-other'
            if changed == 'type': document[0]['targets']['in_scope'][0]['asset_type'] = 'URL'
            if changed == 'negative':
                document[0]['targets']['in_scope'][0]['instruction'] = 'These targets are NOT in scope:\n```\naudio.example\n```'
            if changed == 'missing': document[0]['targets']['in_scope'] = []
            if changed == 'duplicate': document.append(copy.deepcopy(document[0]))
            text = json.dumps(document)
            if changed == 'truncated': text = text[:-2]
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows(self.recipe(), text)

    def test_shared_platforms_addresses_urls_and_new_fence_languages_are_not_silently_filtered(self):
        document = self.document()
        document[0]['targets']['in_scope'][0]['instruction'] = 'These targets are in scope:\n```\ntenant.github.io\n```'
        self.assertEqual(extract_rows(self.recipe(), json.dumps(document)), {'DOMAIN,tenant.github.io'})
        for value in ('github.io', '*.github.io', 'storage.shared.example', '8.8.8.8',
                      'https://host.example/private-path', 'host.example\nnot-a-domain',
                      'host.example\ninclude:other'):
            document = self.document()
            document[0]['targets']['in_scope'][0]['instruction'] = (
                'These targets are in scope:\n```\n' + value + '\n```')
            with self.subTest(value=value), self.assertRaises(Invalid):
                extract_rows(self.recipe(), json.dumps(document), shared_hosts=['storage.shared.example'])
        document = self.document()
        document[0]['targets']['in_scope'][0]['instruction'] = (
            'These targets are in scope:\n```json\n["audio.example"]\n```')
        with self.assertRaises(Invalid): extract_rows(self.recipe(), json.dumps(document))

    def test_wildcard_and_typed_urls_keep_source_scope_and_do_not_take_unlisted_products(self):
        recipe = {**self.recipe(), 'assets': [
            {'type': 'WILDCARD', 'read': 'identifier'},
            {'type': 'URL', 'read': 'identifier', 'within-wildcards': True, 'purpose-prefix': 'Audio API.'}]}
        document = self.document()
        document[0]['targets']['in_scope'] = [
            self.asset('WILDCARD', '*.audio.example'),
            self.asset('URL', 'https://api.audio.example/v1', 'Audio API.'),
            self.asset('URL', 'https://outside.example/', 'Audio API.')]
        self.assertEqual(extract_rows(recipe, json.dumps(document)), {
            'DOMAIN-WILDCARD,*.audio.example', 'DOMAIN,api.audio.example'})
        with self.assertRaises(Invalid): extract_rows({**recipe, 'complete': True}, json.dumps(document))

    def test_a_company_wildcard_does_not_identify_a_new_products_purpose(self):
        recipe = {**self.recipe(), 'assets': [
            {'type': 'WILDCARD', 'read': 'identifier'},
            {'type': 'URL', 'read': 'identifier', 'within-wildcards': True}]}
        document = self.document()
        document[0]['targets']['in_scope'] = [
            self.asset('WILDCARD', '*.audio.example'),
            self.asset('URL', 'https://new-ai.audio.example/', 'A separate AI voice product.')]
        with self.assertRaises(Invalid): extract_rows(recipe, json.dumps(document))

    def config(self):
        source = 'https://publisher.example/security-assets.json'
        audio = self.recipe()
        portal = {**self.recipe(), 'assets': [
            {'type': 'OTHER', 'label': 'Developer portal', 'read': 'fenced-domains'}]}
        fine = [{'id': name, 'priority': rank, 'mode': 'compiled', 'section': 'products',
                 'policy-hint': 'global', 'description': name, 'boundary': '按来源用途分配',
                 'sources': [source], 'extract': [{**recipe, 'source': source}]}
                for name, rank, recipe in [('audio', 20, audio), ('portal', 30, portal)]]
        whole = {**self.whole(), 'assets': audio['assets'] + portal['assets']}
        combined = {'id': 'products-all', 'mode': 'view', 'priority': 10, 'section': 'products',
                    'description': '合集', 'boundary': '替代两项细分', 'members': ['audio', 'portal']}
        specs = [{'id': 'whole-program', 'source': source, 'recipe': whole, 'owners': ['audio', 'portal']}]
        specs.extend({'id': entry['id'], 'source': source, 'recipe': recipe, 'owners': [entry['id']]}
                     for entry, recipe in zip(fine, (audio, portal)))
        return {'schema-version': 2, 'entries': [combined, *fine], 'source-inventories': specs,
                'sections': [{'id': 'products', 'title': '产品'}], 'shared-negatives': [],
                'critical': {'audio.example': ['audio'], 'portal.example': ['portal']}}

    def test_partial_product_readers_require_the_full_program_and_own_purpose_inventory(self):
        from loon_rules.generation import pipeline
        config = self.config()
        pipeline.validate_declarations(config)
        for missing in ('whole-program', 'audio'):
            changed = copy.deepcopy(config)
            changed['source-inventories'] = [spec for spec in changed['source-inventories'] if spec['id'] != missing]
            with self.subTest(missing=missing), self.assertRaises(Invalid):
                pipeline.validate_declarations(changed)
        changed = copy.deepcopy(config)
        changed['source-inventories'][0]['recipe']['assets'] = changed['source-inventories'][0]['recipe']['assets'][1:]
        with self.assertRaises(Invalid): pipeline.validate_declarations(changed)

    def test_full_asset_audit_records_types_and_unselected_targets_before_publishing(self):
        from loon_rules.generation import reporting
        spec = self.config()['source-inventories'][0]
        document = self.document()
        document[0]['targets']['in_scope'].append(self.asset('OTHER', 'Developer portal', '~~~\nportal.example'))
        rows = {'audio': ['DOMAIN-SUFFIX,audio.example', 'DOMAIN,cdn.tenant.example'],
                'portal': ['DOMAIN-SUFFIX,portal.example']}
        state = reporting.audit_inventory(spec, {spec['source']: json.dumps(document)}, rows)
        self.assertEqual(state['program-assets']['assets'], 3)
        self.assertEqual(state['program-assets']['asset-types'], {'OTHER': 2, 'SOURCE_CODE': 1})
        self.assertEqual(state['program-assets']['unselected-assets'], 0)
        reporting.verify_inventories([spec], {spec['id']: state})
        changed = copy.deepcopy(state)
        changed['program-assets']['unselected-assets'] = 1
        with self.assertRaises(Invalid): reporting.verify_inventories([spec], {spec['id']: changed})

    def test_metadata_only_assets_cannot_hide_a_new_network_target(self):
        recipe = self.whole()
        recipe['assets'] += [{'type': 'OTHER', 'label': 'Metadata', 'read': 'no-network-target',
                              'reason': '仅为项目标题，没有网络目标'}]
        document = self.document()
        document[0]['targets']['in_scope'].append(self.asset('OTHER', 'Metadata', 'General information'))
        extract_rows(recipe, json.dumps(document))
        for instruction in ('Use https://new-api.other.example/v2', 'new-api.other.example',
                            '```\nnew-api.other.example\n```', 'Network 8.8.8.0/24',
                            'Network 2001:4860:4860::8888', 'Network AS399358'):
            document[0]['targets']['in_scope'][-1]['instruction'] = instruction
            with self.subTest(instruction=instruction), self.assertRaises(Invalid):
                extract_rows(recipe, json.dumps(document))

    def test_product_purpose_selects_a_typed_api_without_predeclaring_its_address(self):
        recipe = {**self.recipe(), 'assets': [{'type': 'API', 'read': 'identifier',
                  'purpose-contains': 'Advertising conversion API'}]}
        document = self.document()
        document[0]['targets']['in_scope'] = [
            self.asset('API', 'https://new-provider.example/v2', 'Core service. Advertising conversion API.'),
            self.asset('API', 'https://other.example/v2', 'Other product API.')]
        self.assertEqual(extract_rows(recipe, json.dumps(document)), {'DOMAIN,new-provider.example'})
        document[0]['targets']['in_scope'][0]['instruction'] = 'Other product API.'
        with self.assertRaises(Invalid): extract_rows(recipe, json.dumps(document))

    def test_product_purpose_identity_ignores_markdown_spacing_not_its_words(self):
        recipe = {**self.recipe(), 'assets': [{'type': 'URL', 'read': 'identifier',
                  'purpose-prefix': '[Non-core asset] Product website only'}]}
        document = self.document()
        document[0]['targets']['in_scope'] = [
            self.asset('URL', 'https://new-provider.example/', '[Non-core asset]\n\nProduct website only and its API.')]
        self.assertEqual(extract_rows(recipe, json.dumps(document)), {'DOMAIN,new-provider.example'})
        document[0]['targets']['in_scope'][0]['instruction'] = '[Non-core asset]\nProduct archive only.'
        with self.assertRaises(Invalid): extract_rows(recipe, json.dumps(document))

    def test_source_growth_reaches_fine_bundle_and_clients_and_unknown_inputs_preserve_all_outputs(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from checks.source_fixtures import prepare_workspace
        from loon_rules.generation import pipeline
        from loon_rules.exports import publish

        config = self.config()
        source = config['source-inventories'][0]['source']
        document = self.document()
        document[0]['targets']['in_scope'].append(self.asset('OTHER', 'Developer portal', '~~~\nportal.example'))
        inputs = {source: json.dumps(document)}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules' / 'loon').mkdir(parents=True, exist_ok=True)
            (root / 'config/endpoint-contracts.json').write_text('[]')
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for key, entry in entries.items():
                rows = ['DOMAIN-SUFFIX,audio.example', 'DOMAIN,cdn.tenant.example'] if key == 'audio' else ['DOMAIN-SUFFIX,portal.example']
                if key == 'products-all': rows += ['DOMAIN-SUFFIX,audio.example', 'DOMAIN,cdn.tenant.example']
                (root / 'rules' / 'loon' / pipeline.rule_filename(entry)).write_text(
                    pipeline.decorate(entry, rows, None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                for host in ('unprefilled.first-provider.example', 'unprefilled.second-provider.example'):
                    instruction = document[0]['targets']['in_scope'][0]['instruction']
                    document[0]['targets']['in_scope'][0]['instruction'] = (
                        instruction.rsplit('\n```', 1)[0] + '\n' + host + '\n```')
                    inputs[source] = json.dumps(document)
                    pipeline.run()
                    publish(root)
                    for name in ('020-audio', '010-products-all'):
                        path = root / 'rules' / 'loon' / (name + '.lsr')
                        self.assertIn('DOMAIN,' + host, path.read_text())
                        self.assertEqual(path.read_bytes(), (path.parent.with_name('surge') / path.with_suffix('.list').name).read_bytes())
                        for client in ('sing-box', 'mihomo', 'v2ray'):
                            with self.subTest(client=client):
                                self.assertTrue(any(host in file.read_text() for file in (root / 'rules' / client).rglob('*') if file.is_file()))
                    self.assertEqual(pipeline.run(offline=True), 0)
                accepted = copy.deepcopy(document)
                for changed in ('new-product', 'changed-type', 'identity', 'shared-scope', 'lost-domain', 'truncated'):
                    before = {file: file.read_bytes() for folder in ('rules', 'dist', 'data')
                              for file in (root / folder).rglob('*') if file.is_file()}
                    document = copy.deepcopy(accepted)
                    if changed == 'new-product': document[0]['targets']['in_scope'].append(self.asset('OTHER', 'New product', '```\nother.example\n```'))
                    if changed == 'changed-type': document[0]['targets']['in_scope'][0]['asset_type'] = 'CIDR'
                    if changed == 'identity': document[0]['name'] = 'Other company'
                    if changed == 'shared-scope': document[0]['targets']['in_scope'][0]['instruction'] = 'These targets are in scope:\n```\ngithub.io\n```'
                    if changed == 'lost-domain':
                        document[0]['targets']['in_scope'][0]['instruction'] = (
                            document[0]['targets']['in_scope'][0]['instruction'].replace('unprefilled.first-provider.example\n', ''))
                    inputs[source] = json.dumps(document)
                    if changed == 'truncated': inputs[source] = inputs[source][:-2]
                    with self.subTest(changed=changed), self.assertRaises(Invalid): pipeline.run()
                    self.assertEqual(before, {file: file.read_bytes() for folder in ('rules', 'dist', 'data')
                                              for file in (root / folder).rglob('*') if file.is_file()})
