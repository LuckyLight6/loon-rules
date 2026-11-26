"""Keep product categories, bundles and their real execution positions in agreement."""
import json
import unittest
from copy import deepcopy

from loon_rules.generation import pipeline
from loon_rules.rules import Invalid


class SemanticCatalog(unittest.TestCase):
    def load(self):
        config=json.loads((pipeline.ROOT/'config/catalog.json').read_text())
        return config,pipeline.validate_declarations(config)

    def test_every_requested_business_category_has_a_bundle_and_its_fine_members(self):
        config,entries=self.load()
        required={'overseas-development-all','overseas-social-all','overseas-payments-all',
                  'overseas-crypto-all','overseas-productivity-all','mainland-development-all',
                  'mainland-social-all','mainland-payments-all','mainland-daily-services-all',
                  'global-platforms-all','mainland-platforms-all'}
        for key in required:
            with self.subTest(bundle=key):
                view=entries[key]
                self.assertEqual(view['mode'],'view')
                self.assertTrue(view['members'])
                self.assertTrue(all(entries[member]['mode']!='view' for member in view['members']))
                self.assertLess(view['priority'],min(entries[member]['priority'] for member in view['members']))

    def test_ai_products_are_in_two_contiguous_groups_without_addition_batches(self):
        config,entries=self.load();band=next(b for b in config['routing-bands'] if b['start']==1000)
        self.assertEqual([g['id'] for g in band['groups']],['overseas-ai','chinese-ai-international'])
        foreign=entries['ai-overseas-all']['members'];international=entries['ai-cn-international-all']['members']
        self.assertGreater(len(foreign),70);self.assertEqual(len(international),12)
        self.assertLess(max(entries[key]['priority'] for key in foreign),entries['ai-cn-international-all']['priority'])
        index=pipeline.render_index(config,entries)
        sections=[section for section in index.split('\n## ')
                  if section.split('\n',1)[0].endswith(' '+band['title'])]
        self.assertEqual(len(sections),1)
        ai=sections[0]
        for key in foreign:
            self.assertEqual(entries[key]['routing-group'],'overseas-ai')
            self.assertIn('rule-'+key,ai)
        for key in international:
            self.assertEqual(entries[key]['routing-group'],'chinese-ai-international')
            self.assertIn('rule-'+key,ai)
        for label in ('更多产品','更多国际入口','其他产品','其他国际产品','浏览器与开放代理'):
            self.assertNotIn(label,ai)

    def test_music_short_video_and_live_streaming_cannot_drift_into_one_header(self):
        _,entries=self.load()
        for key in ('qq-music','kugou-music','netease-music'):
            self.assertEqual(entries[key]['routing-group'],'mainland-audio')
        for key in ('douyin-mainland-video','kuaishou-video','douyu-live','huya-live'):
            self.assertEqual(entries[key]['routing-group'],'mainland-short-and-live')
        self.assertGreater(entries['kuaishou-video']['priority'],entries['netease-music']['priority'])

    def test_mainland_vendor_exceptions_follow_overseas_products_and_precede_shared_parents(self):
        _,entries=self.load()
        for key in ('qualcomm-mainland','nvidia-mainland','cloudflare-mainland','amazon-mainland'):
            self.assertGreater(entries[key]['priority'],entries['microsoft-platform-services']['priority'])
            self.assertLess(entries[key]['priority'],entries['global-platforms-all']['priority'])
        self.assertLess(entries['cloudflare-public-dns']['priority'],entries['general-ad-and-tracking']['priority'])
        self.assertEqual(entries['workos-authentication']['section'],'development')
        self.assertEqual(entries['xiaohongshu-community']['section'],'social')
        self.assertEqual(entries['zhihu-community']['section'],'social')
        self.assertGreater(entries['global-platforms-all']['priority'],entries['extended-ad-and-tracking']['priority'])
        self.assertGreater(entries['global-platforms-all']['priority'],entries['wps-office']['priority'])

    def test_a_product_number_cannot_silently_put_it_under_a_different_business_header(self):
        config,entries=self.load()
        target=next(e for e in config['entries'] if e['id']=='kuaishou-video')
        target['priority']=entries['qq-music']['priority']+1
        with self.assertRaisesRegex(Invalid,'分类与优先级'):
            pipeline.validate_declarations(config)

    def test_apple_complete_bundle_includes_all_apple_fine_tables(self):
        _,entries=self.load()
        self.assertIn('apple-certificate-validation',entries['apple-all']['members'])
        self.assertIn('apple-other-services',entries['apple-all']['members'])
        self.assertIn('apple-intelligence-relays',entries['apple-all']['members'])
        self.assertNotIn('apple-intelligence-relays',entries['ai-overseas-all']['members'])
