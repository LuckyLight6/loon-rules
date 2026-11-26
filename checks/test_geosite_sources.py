"""Preserve upstream product categories without fixing their domains in selectors."""
import copy
from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class GeositeSources(PublicSourceExamples):
    def recipe(self):
        return {'format': 'geosite-domain-list',
                'attributes': {'ads': '上游广告标记只说明用途，不替代独立拦截策略'},
                'omit-types': {'keyword': '关键词会扩大到无法证明归属的域名',
                               'regexp': '正则范围没有可核对的完整产品边界'}}

    def test_full_product_sources_follow_new_roots_and_keep_exact_shared_tenants(self):
        recipe = self.recipe()
        body = ('product.example\nfull:cdn.vendor.shared.example\n'
                'domain:assets.product.example\nfull:ads.product.example @ads\n'
                'keyword:product\nregexp:.*product.*')
        actual = extract_rows(recipe, body)
        self.assertEqual(actual, {'DOMAIN-SUFFIX,product.example',
                                 'DOMAIN-SUFFIX,assets.product.example',
                                 'DOMAIN,cdn.vendor.shared.example', 'DOMAIN,ads.product.example'})
        self.assertIn('DOMAIN-SUFFIX,new-provider.example',
                      extract_rows(recipe, body + '\nnew-provider.example'))
        for extra in ('include:unknown', 'full:bad.internal', 'IP-CIDR:8.8.8.0/24',
                      'new-provider.example @unreviewed', 'github.io', '../escape.example'):
            with self.subTest(extra=extra), self.assertRaises(Invalid):
                extract_rows(recipe, body + '\n' + extra)

    def test_source_type_omissions_need_reasons_and_unknown_types_cannot_be_silenced(self):
        recipe = self.recipe()
        for changes in ({'omit-types': {'keyword': ''}},
                        {'omit-types': {'unknown': '不接受未识别的类型'}},
                        {'attributes': {'ads': ''}}):
            with self.subTest(changes=changes), self.assertRaises(Invalid):
                extract_rows({**recipe, **changes}, 'product.example')
        with self.assertRaises(Invalid):
            extract_rows({'format': 'geosite-domain-list'}, 'product.example\nkeyword:product')

    def test_named_product_blocks_follow_new_domains_without_reading_the_next_business(self):
        recipe = {**self.recipe(), 'include-comment-blocks': {
            'Audio product': '该块由上游明确标明产品用途'}}
        body = ('company.example\n\n# Audio product\naudio.example\n'
                'full:media.provider.example\n\n# Other product\nother.example')
        expected = {'DOMAIN-SUFFIX,audio.example', 'DOMAIN,media.provider.example'}
        self.assertEqual(extract_rows(recipe, body), expected)
        changed = body.replace('audio.example', 'audio.example\nnew-audio-service.example')
        self.assertEqual(extract_rows(recipe, changed), expected | {'DOMAIN-SUFFIX,new-audio-service.example'})
        for changed in (body.replace('# Audio product', '# Renamed'),
                        body + '\n# Audio product\nsecond.example',
                        body.replace('full:media.provider.example', 'include:unclassified')):
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows(recipe, changed)
        with self.assertRaises(Invalid):
            extract_rows({**recipe, 'include-comment-blocks': {'Audio product': ''}}, body)

    def test_selected_blocks_require_an_independent_unfiltered_inventory(self):
        from loon_rules.generation import pipeline
        config = self.config()
        child = config['entries'][0]
        child['extract'][0]['include-comment-blocks'] = {'Child': '指定产品块'}
        config['source-inventories'][0]['recipe']['include-comment-blocks'] = {'Child': '指定产品块'}
        with self.assertRaisesRegex(Invalid, '筛选前|未筛选|整份'):
            pipeline.validate_declarations(config)
        full = copy.deepcopy(config['source-inventories'][0])
        full['id'] = 'unfiltered-child-source'
        del full['recipe']['include-comment-blocks']
        config['source-inventories'].append(full)
        pipeline.validate_declarations(config)

    def test_product_block_growth_reaches_bundles_and_exports_without_hiding_the_unfiltered_source(self):
        import json
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from checks.source_fixtures import prepare_workspace
        from loon_rules.generation import pipeline
        from loon_rules.exports import publish

        source = 'https://publisher.example/data/company'
        whole = {'format': 'geosite-domain-list'}
        selected = {**whole, 'include-comment-blocks': {'Product': '上游明确的产品块'}}
        fine = {'id': 'product', 'priority': 20, 'mode': 'compiled', 'section': 'products',
                'description': '独立产品', 'boundary': '上游用途块', 'sources': [source],
                'extract': [{**selected, 'source': source}]}
        common = {'id': 'company', 'priority': 30, 'mode': 'compiled', 'section': 'products',
                  'description': '厂商共用服务', 'boundary': '完整来源扣除前面已识别的产品',
                  'sources': [source], 'extract': [{**whole, 'source': source}], 'domain-remainder': True}
        combined = {'id': 'products-all', 'priority': 10, 'mode': 'view', 'section': 'products',
                    'description': '合集', 'boundary': '两表的替代选择', 'members': ['product', 'company']}
        config = {'schema-version': 2, 'entries': [combined, fine, common],
                  'sections': [{'id': 'products', 'title': '产品'}], 'shared-negatives': [],
                  'critical': {'product.example': ['product'], 'company.example': ['company']},
                  'recommended-views': ['products-all'], 'source-inventories': [
                      {'id': 'whole-source', 'source': source, 'recipe': whole, 'owners': ['product', 'company']},
                      {'id': 'product-block', 'source': source, 'recipe': selected, 'owners': ['product']}]}
        inputs = {source: 'company.example\n\n# Product\nproduct.example'}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = Path(tmp)
            (root / 'rules' / 'loon').mkdir(parents=True, exist_ok=True)
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for key, entry in entries.items():
                rows = ['DOMAIN-SUFFIX,product.example'] if key == 'product' else ['DOMAIN-SUFFIX,company.example']
                if key == 'products-all':
                    rows.append('DOMAIN-SUFFIX,product.example')
                (root / 'rules' / 'loon' / pipeline.rule_filename(entry)).write_text(
                    pipeline.decorate(entry, rows, None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                inputs[source] += '\nnew-service.example\n\n# Shared\nnew-company.example'
                pipeline.run()
                pipeline.run()
                publish(root)
                self.assertEqual(pipeline.run(offline=True), 0)
                self.assertIn('DOMAIN-SUFFIX,new-service.example',
                              (root / 'rules/loon/020-product.lsr').read_text())
                self.assertNotIn('new-company.example', (root / 'rules/loon/020-product.lsr').read_text())
                for path in ('rules/loon/010-products-all.lsr', 'rules/surge/010-products-all.list',
                             'rules/sing-box/010-products-all.json'):
                    self.assertIn('new-service.example', (root / path).read_text())
                    self.assertIn('new-company.example', (root / path).read_text())
                before = {path: path.read_bytes() for folder in ('rules', 'dist', 'data')
                          for path in (root / folder).rglob('*') if path.is_file()}
                inputs[source] = inputs[source].replace('# Product', '# Unverified role')
                with self.assertRaises(Invalid):
                    pipeline.run()
                self.assertTrue(all(path.read_bytes() == body for path, body in before.items()))


    def test_unused_notes_apply_only_to_the_adjacent_block_and_are_not_a_withdrawal_signal(self):
        recipe = {**self.recipe(), 'excluded-comment-blocks': {
            'Unused': '上游未使用的候选不自动新增，已有来源支持的入口仍保留'}}
        body = ('# Core\nproduct.example\n\n# Unused\nold-alias.example\n'
                'old-cdn.example\n\nfull:uploads.storage.shared.example\n# Other\nrelated.example')
        expected = {'DOMAIN-SUFFIX,product.example', 'DOMAIN,uploads.storage.shared.example',
                    'DOMAIN-SUFFIX,related.example'}
        self.assertEqual(extract_rows(recipe, body), expected)
        changed = body.replace('old-alias.example', 'new-unused.example')
        self.assertEqual(extract_rows(recipe, changed), expected)
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('# Unused', '# Renamed'))

    def test_include_relations_are_explicit_and_never_flatten_another_product(self):
        recipe = {**self.recipe(), 'delegated-includes': {
            'child': {'owner': 'child-product', 'reason': '独立产品使用独立上游清单'}}}
        body = 'product.example\ninclude:child'
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN-SUFFIX,product.example'})
        for changed in (body + '\ninclude:new-child', body.replace('include:child', ''),
                        body + '\ninclude:child', body.replace('include:child', 'include:../child'),
                        body.replace('include:child', 'include:child @ads')):
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows(recipe, changed)

    def test_shared_platform_scopes_are_delegated_and_audited_against_the_whole_destination(self):
        from loon_rules.generation import reporting
        recipe = {**self.recipe(), 'delegated-scopes': {
            'DOMAIN-SUFFIX,github.io': {'owner': 'platform', 'source': 'https://platform.example/help',
                                      'reason': '平台共享托管范围另行匹配'}}}
        body = 'product.example\ngithub.io'
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN-SUFFIX,product.example'})
        spec = {'id': 'source', 'source': 'feed', 'recipe': recipe, 'owners': ['product']}
        data = {'product': ['DOMAIN-SUFFIX,product.example'], 'platform': ['DOMAIN-SUFFIX,github.io']}
        report = reporting.audit_inventory(spec, {'feed': body}, data)
        self.assertEqual(report['domain-scopes'], 2)
        self.assertEqual(report['outside-scope'], 0)
        reporting.verify_inventories([spec], {'source': report})
        for target in ([], ['DOMAIN,github.io']):
            data['platform'] = target
            report = reporting.audit_inventory(spec, {'feed': body}, data)
            with self.assertRaises(Invalid):
                reporting.verify_inventories([spec], {'source': report})
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('github.io', 'other-private.github.io'))

    def test_first_party_platform_statements_can_identify_a_shared_hosting_namespace(self):
        recipe = {'format': 'product-domain-statements', 'include-list-items': True,
                  'paragraph-contains': ['providers', 'proxied'], 'domain-scope': 'private-platform'}
        body = '<ul><li>Third party providers proxied by the github.io domain</li></ul>'
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN-SUFFIX,github.io'})
        for changed in (body.replace('github.io', 'shared.example'),
                        body.replace('proxied', 'linked'),
                        body.replace('github.io', 'com')):
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows(recipe, changed)

    def config(self):
        base = 'https://publisher.example/data/'
        parent = {**self.recipe(), 'source': base + 'parent', 'delegated-includes': {
            'child': {'owner': 'child-product', 'reason': '子产品单独维护'}}}
        child = {**self.recipe(), 'source': base + 'child'}
        entries = [{'id': key, 'priority': rank, 'mode': 'compiled', 'section': 'products',
                    'description': key, 'boundary': '对应上游分类', 'policy-hint': 'global',
                    'sources': [recipe['source']], 'extract': [recipe]}
                   for key, rank, recipe in [('child-product', 20, child), ('parent-product', 30, parent)]]
        specs = [{'id': entry['id'], 'source': entry['sources'][0], 'owners': [entry['id']],
                  'recipe': {k: v for k, v in entry['extract'][0].items() if k != 'source'}}
                 for entry in entries]
        return {'schema-version': 2, 'entries': entries, 'source-inventories': specs,
                'sections': [{'id': 'products', 'title': '产品'}], 'critical': {}, 'shared-negatives': []}

    def test_a_delegated_category_must_have_the_actual_independent_child_source(self):
        from loon_rules.generation import pipeline
        config = self.config()
        pipeline.validate_declarations(config)
        changed = copy.deepcopy(config)
        child = changed['entries'][0]
        child['sources'] = ['https://unrelated.example/child']
        child['extract'][0]['source'] = child['sources'][0]
        changed['source-inventories'][0]['source'] = child['sources'][0]
        with self.assertRaisesRegex(Invalid, '引用|独立|子分类'):
            pipeline.validate_declarations(changed)
        changed = copy.deepcopy(config)
        changed['source-inventories'][1]['recipe']['delegated-includes'] = {}
        with self.assertRaisesRegex(Invalid, '完整|独立'):
            pipeline.validate_declarations(changed)

    def test_native_inventory_counts_omitted_types_and_delegated_categories(self):
        from loon_rules.generation import reporting
        config = self.config()
        spec = config['source-inventories'][1]
        body = 'product.example\ninclude:child\nkeyword:product\nregexp:.*product.*'
        inputs = {spec['source']: body}
        data = {'parent-product': ['DOMAIN-SUFFIX,product.example']}
        report = reporting.audit_inventory(spec, inputs, data)
        self.assertEqual(report['other-rules'], 3)
        self.assertEqual(report['omitted-rule-types'], {'keyword': 1, 'regexp': 1})
        self.assertEqual(report['delegated-includes'], ['child'])

    def test_native_category_cycles_are_not_accepted_as_complete_membership(self):
        from loon_rules.generation import pipeline
        config = self.config()
        child = config['entries'][0]
        delegation = {'parent': {'owner': 'parent-product', 'reason': '错误循环'}}
        child['extract'][0]['delegated-includes'] = delegation
        config['source-inventories'][0]['recipe']['delegated-includes'] = delegation
        with self.assertRaisesRegex(Invalid, '循环'):
            pipeline.validate_declarations(config)

    def test_source_updates_reach_fine_rules_bundles_and_exports_and_invalid_splits_write_nothing(self):
        import json
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from checks.source_fixtures import prepare_workspace
        from loon_rules.generation import pipeline
        from loon_rules.exports import publish

        config = self.config()
        view = {'id': 'products-all', 'priority': 10, 'mode': 'view', 'section': 'products',
                'description': '产品合集', 'boundary': '替代所列细分',
                'members': ['child-product', 'parent-product']}
        config['entries'].insert(0, view)
        config['recommended-views'] = ['products-all']
        config['critical'] = {'product.example': ['parent-product'],
                              'child.example': ['child-product']}
        base = 'https://publisher.example/data/'
        inputs = {base + 'parent': 'product.example\ninclude:child',
                  base + 'child': 'child.example'}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules' / 'loon').mkdir(parents=True, exist_ok=True)
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for key, entry in entries.items():
                rows = ['DOMAIN-SUFFIX,child.example'] if key == 'child-product' else ['DOMAIN-SUFFIX,product.example']
                if key == 'products-all':
                    rows.append('DOMAIN-SUFFIX,child.example')
                (root / 'rules' / 'loon' / pipeline.rule_filename(entry)).write_text(
                    pipeline.decorate(entry, rows, None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                inputs[base + 'parent'] += '\nnew-product-service.example'
                inputs[base + 'child'] += '\nfull:files.new-provider.example'
                pipeline.run()
                pipeline.run()
                publish(root)
                self.assertEqual(pipeline.run(offline=True), 0)
                for key in ('parent-product', 'products-all'):
                    path = root / 'rules' / 'loon' / pipeline.rule_filename(entries[key])
                    self.assertIn('DOMAIN-SUFFIX,new-product-service.example', pipeline.rules.read_rules(path.read_text()))
                    self.assertEqual(path.read_bytes(), (path.parent.with_name('surge') / path.with_suffix('.list').name).read_bytes())
                    exported = root / 'rules/sing-box' / path.with_suffix('.json').name
                    self.assertIn('new-product-service.example', exported.read_text())
                child = root / 'rules' / 'loon' / pipeline.rule_filename(entries['child-product'])
                self.assertIn('DOMAIN,files.new-provider.example', pipeline.rules.read_rules(child.read_text()))
                before = {path: path.read_bytes() for folder in ('rules', 'dist', 'data')
                          for path in (root / folder).rglob('*') if path.is_file()}
                inputs[base + 'parent'] += '\ninclude:unclassified'
                with self.assertRaises(Invalid):
                    pipeline.run()
                self.assertTrue(all(path.read_bytes() == body for path, body in before.items()))
