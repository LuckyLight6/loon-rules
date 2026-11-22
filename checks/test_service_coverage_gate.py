"""Reject incomplete service membership and routes before publishing subscriptions."""
import unittest
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from loon_rules.generation import reporting
from loon_rules.generation import contracts
from loon_rules.generation import pipeline
from loon_rules.generation.membership import project_domains
from loon_rules.rules import Invalid
from loon_rules.sources import coverage
from loon_rules.sources.inputs import extract_rows
from checks.source_fixtures import prepare_workspace


class ServiceCoverageGate(unittest.TestCase):
    def test_a_selected_service_scope_cannot_be_claimed_by_an_unrelated_product(self):
        source = 'https://publisher.example/product.list'
        entries = {
            'wrong': {'priority': 10, 'mode': 'compiled'},
            'product': {'priority': 20, 'mode': 'compiled',
                        'projection': [{'source': source, 'roots': ['vendor.example']}]},
        }
        data = {'wrong': ['DOMAIN-SUFFIX,vendor.example'], 'product': []}
        with self.assertRaisesRegex(Invalid, '归属|抢先'):
            coverage.audit(entries, data, {source: 'DOMAIN-SUFFIX,vendor.example'},
                           order=['wrong', 'product'],
                           selected={'product': {source: {'DOMAIN-SUFFIX,vendor.example'}}})

    def test_unclassified_source_rows_prevent_a_publish_instead_of_only_showing_review(self):
        specs = [{'id': 'vendor', 'source': 'feed', 'owners': ['product']}]
        pools = {'product': ['DOMAIN-SUFFIX,vendor.example']}
        source = {'feed': 'DOMAIN-SUFFIX,vendor.example\nDOMAIN,new.other.example'}
        status = {'vendor': reporting.audit_inventory(specs[0], source, pools)}
        with self.assertRaisesRegex(Invalid, 'vendor'):
            reporting.verify_inventories(specs, status)
        for failed in ({'state': 'unavailable'}, {'state': 'invalid'}):
            with self.subTest(failed=failed), self.assertRaises(Invalid):
                reporting.verify_inventories(specs, {'vendor': failed})

    def test_an_inventory_checks_first_owner_and_the_whole_wildcard(self):
        spec = {'id': 'vendor', 'source': 'feed', 'owners': ['product']}
        source = {'feed': 'DOMAIN-WILDCARD,*.files.vendor.example'}
        data = {'wrong': ['DOMAIN-SUFFIX,vendor.example'],
                'product': ['DOMAIN-SUFFIX,files.vendor.example']}
        status = reporting.audit_inventory(spec, source, data, order=['wrong', 'product'])
        self.assertEqual(status['domain-scopes'], 1)
        self.assertEqual(status['outside-scope'], 1)
        with self.assertRaises(Invalid):
            reporting.verify_inventories([spec], {'vendor': status})
        status = reporting.audit_inventory(spec, source, data, order=['product', 'wrong'])
        reporting.verify_inventories([spec], {'vendor': status})
        data['product'] = ['DOMAIN,one.files.vendor.example']
        status = reporting.audit_inventory(spec, source, data, order=['product', 'wrong'])
        self.assertEqual(status['outside-scope'], 1)

    def test_whole_company_source_follows_new_domains_without_importing_ip_or_process_rules(self):
        source = ['DOMAIN-SUFFIX,vendor.example', 'DOMAIN,new.vendor.test',
                  'DOMAIN-WILDCARD,files-*.vendor.example',
                  'IP-CIDR,17.0.0.0/8,no-resolve', 'PROCESS-NAME,vendor']
        self.assertEqual(project_domains(source, {'all-domains': True}), source[:3])
        for flag in ('roots', 'exact'):
            with self.subTest(flag=flag), self.assertRaises(Invalid):
                project_domains(source, {'all-domains': True, flag: ['vendor.example']})

    def test_official_domain_lists_select_vendor_hosts_and_leave_shared_dependencies_separate(self):
        body = ('<p>Vendor uses the following domains</p><ul>'
                '<li>*.vendor.example.com</li><li>files.new-vendor.example.com</li>'
                '<li>challenge.shared.example.com</li></ul>')
        recipe = {'format': 'purpose-domain-lists', 'labels': ['uses the following domains'],
                  'select': {'roots': ['vendor.example.com', 'new-vendor.example.com']}}
        self.assertEqual(extract_rows(recipe, body),
                         {'DOMAIN-WILDCARD,*.vendor.example.com', 'DOMAIN,files.new-vendor.example.com'})
        spec = {'id': 'vendor', 'source': 'article', 'format': 'purpose-domain-lists',
                'labels': recipe['labels'],
                'routes': {'product': ['*.vendor.example.com', 'files.new-vendor.example.com']},
                'shared': {'challenge.shared.example.com': 'Used by several products'}}
        contracts.verify_sources([spec], {'article': body})
        changed = body.replace('</ul>', '<li>api.next-vendor.example.com</li></ul>')
        with self.assertRaisesRegex(Invalid, '待归属'):
            contracts.verify_sources([spec], {'article': changed})

    def test_a_structured_inventory_follows_the_whole_official_service_list(self):
        spec = {'id': 'regions', 'source': 'vendor-domains', 'owners': ['vendor'],
                'recipe': {'format': 'brand-domain-list', 'brand-label': 'brand'}}
        data = {'vendor': ['DOMAIN-SUFFIX,brand.com', 'DOMAIN-SUFFIX,brand.co.jp']}
        source = {'vendor-domains': '.brand.com\n.brand.co.jp'}
        status = reporting.audit_inventory(spec, source, data)
        self.assertEqual(status['domain-scopes'], 2)
        reporting.verify_inventories([spec], {'regions': status})
        source['vendor-domains'] += '\n.brand.de'
        status = reporting.audit_inventory(spec, source, data)
        with self.assertRaises(Invalid):
            reporting.verify_inventories([spec], {'regions': status})

    def test_inventory_ownership_accepts_the_fine_members_of_an_alternative_bundle(self):
        spec = {'id': 'vendor', 'source': 'feed', 'owners': ['vendor-all']}
        source = {'feed': 'DOMAIN-SUFFIX,vendor.example'}
        data = {'vendor-all': ['DOMAIN-SUFFIX,vendor.example'],
                'product': ['DOMAIN-SUFFIX,vendor.example']}
        entries = {'vendor-all': {'members': ['product']}, 'product': {}}
        status = reporting.audit_inventory(spec, source, data, order=['product'], entries=entries)
        reporting.verify_inventories([spec], {'vendor': status})

    def test_another_product_shared_dependency_does_not_remove_the_company_parent(self):
        company = {'id': 'company', 'priority': 30, 'section': 'company', 'mode': 'compiled',
                   'description': '公司通用服务', 'boundary': '公司自己的服务',
                   'sources': ['feed'], 'fallback': True, 'domain-remainder': True,
                   'projection': [{'source': 'feed', 'all-domains': True}]}
        product = {'id': 'product', 'priority': 20, 'section': 'product', 'mode': 'compiled',
                   'description': '另一家公司', 'boundary': '独立产品', 'sources': ['article'],
                   'include': ['DOMAIN,other.example.com']}
        config = {'schema-version': 2, 'entries': [product, company], 'critical': {},
                  'shared-negatives': [], 'sections': [
                      {'id': 'company', 'title': '公司', 'numbers': [30]},
                      {'id': 'product', 'title': '产品', 'numbers': [20]}],
                  'source-inventories': [{'id': 'company', 'source': 'feed', 'owners': ['company']}]}
        contract = {'id': 'product', 'source': 'article', 'format': 'named-endpoints',
                    'routes': {'product': ['other.example.com']},
                    'shared': {'captcha.vendor.com': 'A shared external dependency'},
                    'guard-sections': ['product']}
        inputs = {'feed': 'DOMAIN-SUFFIX,vendor.com',
                  'article': 'other.example.com captcha.vendor.com'}
        with TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            with patch.object(pipeline, 'ROOT', root):
                (root / 'rules').mkdir()
                entries = pipeline.validate_declarations(config)
                for entry, rows in ((company, ['DOMAIN-SUFFIX,vendor.com']),
                                    (product, ['DOMAIN,other.example.com'])):
                    (root / 'rules' / pipeline.rule_filename(entry)).write_text(
                        pipeline.decorate(entry, rows, None, '2020-01-01T00:00:00Z'))
                (root / 'config/catalog.json').write_text(json.dumps(config))
                (root / 'config/endpoint-contracts.json').write_text(json.dumps([contract]))
                (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
                with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                    self.assertEqual(pipeline.run(), 0)
                published = root / 'rules' / pipeline.rule_filename(company)
                self.assertEqual(pipeline.rules.read_rules(published.read_text()), ['DOMAIN-SUFFIX,vendor.com'])

