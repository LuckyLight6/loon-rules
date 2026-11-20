import json
import unittest
import library as lib

class BusinessOrder(unittest.TestCase):
    def test_google_and_overseas_services_precede_domestic_groups(self):
        config=json.loads((lib.ROOT/'catalog.json').read_text())
        es=lib.validate_declarations(config)
        order=lib.route_order(config,es)
        for first,last in [('gemini-connections','google-account-authentication'),
                           ('google-account-authentication','wechat-shared-and-mainland'),
                           ('google-drive-and-documents','microsoft-account-authentication'),
                           ('steam-global-platform','steam-mainland-downloads'),
                           ('discord-messaging-and-voice','google-platform-services'),
                           ('ai-cn-international','ai-cn'),
                           ('paypal-payments','taobao-and-xianyu-shopping')]:
            self.assertLess(order.index(first),order.index(last),(first,last))

    def test_every_selection_has_exactly_one_published_position(self):
        cfg=json.loads((lib.ROOT/'catalog.json').read_text())
        all_ids=[k for band in cfg['routing-bands'] for k in band['ids']]
        self.assertCountEqual(all_ids,[e['id'] for e in cfg['entries']])
