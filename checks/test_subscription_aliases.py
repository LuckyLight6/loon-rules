"""A priority change keeps public download paths without creating another rule group."""
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from checks.source_fixtures import prepare_workspace
from loon_rules.generation import pipeline
from loon_rules.exports import publish
from loon_rules.rules import Invalid


class SubscriptionAliases(unittest.TestCase):
    def test_early_optional_ads_keep_dedicated_subdomains_and_protect_product_entries(self):
        ads = {'id': 'ads', 'mode': 'managed', 'priority': 240, 'section': 'privacy',
               'selection': 'optional', 'description': '可选拦截', 'boundary': '专用广告优先，正常网站保留',
               'sources': ['ads-feed'], 'kinds': ['DOMAIN', 'DOMAIN-SUFFIX'], 'flags': [], 'license': 'MIT',
               'policy-hint': 'reject', 'fallback': True, 'domain-remainder': True, 'protect-site-scopes': True}
        product = {'id': 'product', 'mode': 'compiled', 'priority': 1000, 'section': 'products',
                   'description': '产品', 'boundary': '产品服务', 'sources': ['product-feed'],
                   'projection': [{'source': 'product-feed', 'roots': ['product.example']}]}
        config = {'schema-version': 2, 'priority-width': 4, 'entries': [ads, product],
                  'subscription-aliases': {'7800-ads': 'ads'},
                  'critical': {'api.product.example': ['product']}, 'shared-negatives': [],
                  'sections': [{'id': 'privacy', 'title': '广告与隐私'}, {'id': 'products', 'title': '产品'}]}
        inputs = {'ads-feed': 'DOMAIN-SUFFIX,ads.product.example\nDOMAIN-SUFFIX,product.example',
                  'product-feed': 'DOMAIN-SUFFIX,product.example'}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules').mkdir()
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for entry, body in ((ads, inputs['ads-feed']), (product, inputs['product-feed'])):
                (root / 'rules' / pipeline.rule_filename(entries[entry['id']])).write_text(
                    pipeline.decorate(entries[entry['id']], body.splitlines(), None, '2026-11-20T00:00:00Z'))
            alias = root / 'rules/7800-ads.lsr'
            alias.write_text('# name: ads\nDOMAIN,previous.example\n')
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                pipeline.run()
            canonical = root / 'rules/0240-ads.lsr'
            self.assertEqual(alias.read_bytes(), canonical.read_bytes())
            rows = {key: pipeline.rules.read_rules((root / 'rules' / pipeline.rule_filename(entry)).read_text())
                    for key, entry in entries.items()}
            self.assertEqual(rows['ads'], ['DOMAIN-SUFFIX,ads.product.example'])
            order = pipeline.subscription_order(config, entries)
            self.assertEqual(pipeline.ordered_route('ads.product.example', order, rows), 'ads')
            self.assertEqual(pipeline.ordered_route('api.product.example', order, rows), 'product')
            self.assertEqual(pipeline.ordered_route('ads.product.example', ['product'], rows), 'product')
            self.assertEqual(pipeline.run(offline=True), 0)
            publish(root)
            self.assertEqual(alias.with_suffix('.list').read_bytes(), canonical.read_bytes())
            manifest = json.loads((root / 'dist/manifest.json').read_text())
            self.assertEqual(len(manifest['formats']['loon']['rules']), 2)
            alias.write_text('# name: ads\nDOMAIN,stale.example\n')
            with self.assertRaisesRegex(Invalid, '兼容下载'):
                pipeline.run(offline=True)
