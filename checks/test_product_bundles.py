"""The requested product bundles remain alternatives to the fine subscriptions."""
import json
import unittest

from loon_rules.generation import pipeline


class ProductBundles(unittest.TestCase):
    def test_each_requested_region_and_product_family_has_a_real_bundle(self):
        config = json.loads((pipeline.ROOT / 'config/catalog.json').read_text())
        entries = pipeline.validate_declarations(config)
        required = {'ai-overseas-all', 'ai-cn-international-all', 'ai-cn-all',
                    'ai-overseas-mainland-all', 'overseas-media-all', 'overseas-games-all',
                    'mainland-media-all', 'mainland-games-all'}
        self.assertTrue(required <= set(entries), '缺少请求的产品合集：' + ', '.join(sorted(required - set(entries))))
        for key in required:
            entry = entries[key]
            with self.subTest(bundle=key):
                self.assertEqual(entry['mode'], 'view')
                self.assertTrue(entry['members'])
                for member in entry['members']:
                    self.assertNotEqual(entries[member]['mode'], 'view')
                    self.assertTrue((pipeline.ROOT / 'rules' / pipeline.rule_filename(entries[member])).is_file())
        self.assertIn('jetbrains-ai-mainland', entries['ai-overseas-mainland-all']['members'])
        self.assertNotIn('jetbrains-ai-mainland', entries['ai-cn-all']['members'])
        self.assertIn('steam-international-platform', entries['overseas-games-all']['members'])
        self.assertNotIn('steam-mainland-downloads', entries['overseas-games-all']['members'])
        self.assertIn('steam-mainland-downloads', entries['mainland-games-all']['members'])
        self.assertIn('qq-music', entries['mainland-media-all']['members'])
        self.assertNotIn('netflix-video-and-delivery', entries['mainland-media-all']['members'])
