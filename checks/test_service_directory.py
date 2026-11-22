"""Keep the company/product directory tied to the real subscriptions."""
import unittest

from loon_rules.rules import Invalid


class ServiceDirectory(unittest.TestCase):
    def fixture(self):
        entries = {'chat': {'id': 'chat', 'priority': 1010, 'mode': 'compiled', 'description': '对话服务'},
                   'files': {'id': 'files', 'priority': 1020, 'mode': 'compiled', 'description': '文件服务'},
                   'vendor-all': {'id': 'vendor-all', 'priority': 1000, 'mode': 'view',
                                  'description': '厂商合集', 'members': ['chat', 'files']},
                   'local': {'id': 'local', 'priority': 110, 'mode': 'compiled', 'description': '内网'}}
        config = {'entries': list(entries.values()), 'views': ['vendor-all'],
                  'service-directory': {'vendors': [{'id': 'vendor', 'name': '示例厂商',
                      'products': [{'name': '聊天应用', 'rules': ['chat']},
                                   {'name': '云盘', 'rules': ['files']}]}], 'common': ['local']}}
        return config, entries

    def test_directory_renders_company_products_and_real_rule_links(self):
        from loon_rules.generation.directory import render
        config, entries = self.fixture()
        text = render(config, entries)
        self.assertIn('## 示例厂商', text)
        self.assertIn('| 聊天应用 |', text)
        self.assertIn('../rules/1010-chat.lsr', text)
        self.assertIn('../rules/1000-vendor-all.lsr', text)
        self.assertIn('rules.md', text)

    def test_every_real_subscription_needs_a_vendor_or_an_explicit_common_role(self):
        from loon_rules.generation.directory import validate
        config, entries = self.fixture()
        validate(config, entries)
        config['service-directory']['vendors'][0]['products'].pop()
        with self.assertRaisesRegex(Invalid, 'files'):
            validate(config, entries)

    def test_shared_connections_can_serve_multiple_products_of_the_same_company(self):
        from loon_rules.generation.directory import validate
        config, entries = self.fixture()
        vendor = config['service-directory']['vendors'][0]
        vendor['products'].append({'name': '桌面应用', 'rules': ['chat']})
        validate(config, entries)
        config['service-directory']['vendors'].append(
            {'id': 'other', 'name': '另一厂商', 'products': [{'name': '应用', 'rules': ['chat']}]})
        with self.assertRaisesRegex(Invalid, 'chat'):
            validate(config, entries)

    def test_empty_products_unknown_rules_and_aggregate_bodies_are_not_fake_fine_groups(self):
        from loon_rules.generation.directory import validate
        for values in ([], ['missing'], ['vendor-all']):
            config, entries = self.fixture()
            config['service-directory']['vendors'][0]['products'][0]['rules'] = values
            with self.subTest(rules=values), self.assertRaises(Invalid):
                validate(config, entries)

    def test_legacy_library_callers_do_not_need_the_new_company_directory(self):
        from loon_rules.generation.directory import validate, render
        config, entries = self.fixture()
        config.pop('service-directory')
        validate(config, entries)
        self.assertIsNone(render(config, entries))

    def test_company_products_can_split_a_shared_scope_across_business_sections(self):
        from loon_rules.generation import pipeline
        import json
        config = json.loads((pipeline.ROOT / 'config/catalog.json').read_text())
        target = next(entry for entry in config['entries'] if entry['id'] == 'apple-find-my')
        target['section'] = 'media'
        target['routing-group'] = 'overseas-media-content'
        target['priority'] = 3990
        entries = pipeline.validate_declarations(config)
        self.assertEqual(entries[target['id']]['vendor'], 'apple')
        apple = next(v for v in config['service-directory']['vendors'] if v['id']=='apple')
        apple['products'] = [product for product in apple['products'] if target['id'] not in product['rules']]
        config['service-directory']['vendors'].append(
            {'id': 'other', 'name': '其他厂商', 'products': [{'name': '应用', 'rules': [target['id']]}]})
        with self.assertRaises(Invalid):
            pipeline.validate_declarations(config)
