import re
import json
import unittest
from loon_rules.generation import pipeline as lib
from loon_rules.catalog import priority_label

class BusinessOrder(unittest.TestCase):
    def test_shadow_check_covers_wildcards_without_rejecting_partial_overlap(self):
        from loon_rules.rules import Invalid
        entries={'early':{},'later':{}}
        for early,later in [
            ('DOMAIN-SUFFIX,vendor.example','DOMAIN-WILDCARD,p??-api.vendor.example'),
            ('DOMAIN-WILDCARD,*.vendor.example','DOMAIN-SUFFIX,api.vendor.example'),
            ('DOMAIN,api.vendor.example','DOMAIN-WILDCARD,api.vendor.example')]:
            with self.subTest(early=early,later=later),self.assertRaises(Invalid):
                lib.verify_domain_order(['early','later'],entries,{'early':[early],'later':[later]})
        lib.verify_domain_order(['early','later'],entries,{
            'early':['DOMAIN-SUFFIX,api.vendor.example'],
            'later':['DOMAIN-WILDCARD,*.vendor.example']})

    def test_service_address_scope_cannot_be_partly_stolen_by_an_earlier_prefix(self):
        from loon_rules.rules import Invalid
        entries={'early':{},'voice':{},'fallback':{'fallback':True}}
        data={'early':['IP-CIDR,203.0.113.40/32,no-resolve'],
              'voice':['IP-CIDR,203.0.113.0/24,no-resolve'],
              'fallback':['IP-CIDR,203.0.0.0/16']}
        with self.assertRaisesRegex(Invalid,'voice'):
            lib.verify_ip_order(['early','voice','fallback'],entries,data)
        lib.verify_ip_order(['voice','early','fallback'],
                            {**entries,'early':{'fallback':True}},data)

    def test_google_and_overseas_services_precede_domestic_groups(self):
        config=json.loads((lib.ROOT/'config/catalog.json').read_text())
        es=lib.validate_declarations(config)
        order=lib.route_order(config,es)
        for first,last in [('gemini-connections','google-account-authentication'),
                           ('google-account-authentication','wechat-shared-and-mainland'),
                           ('google-drive-and-documents','microsoft-account-authentication'),
                           ('steam-international-platform','steam-mainland-downloads'),
                           ('discord-messaging-and-voice','google-platform-services'),
                           ('google-platform-services','steam-mainland-downloads'),
                           ('microsoft-platform-services','alipay-mainland-payments'),
                           ('apple-app-and-device-verification','apple-shared-store-assets'),
                           ('apple-private-relay-connections','apple-cloud-sync'),
                           ('qwen-international','qwen-mainland'),
                           ('microsoft-platform-services','qwen-mainland'),
                           ('paypal-payments','taobao-and-xianyu-shopping')]:
            self.assertLess(order.index(first),order.index(last),(first,last))

    def test_every_selection_has_exactly_one_published_position(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        all_ids=[k for band in cfg['routing-bands'] for k in band['ids']]
        self.assertCountEqual(all_ids,[e['id'] for e in cfg['entries']])


    def test_reader_order_is_the_routing_order_for_every_selection(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entries=lib.validate_declarations(cfg)
        rows=re.findall(r'^\| (\d+) \| ',lib.render_index(cfg,entries),re.M)
        by_number={priority_label(e):key for key,e in entries.items() if 'priority' in e}
        published=[by_number[n] for n in rows]
        self.assertEqual(published,lib.subscription_order(cfg,entries))
        for selection in ((),*((v,) for v in cfg['views']),cfg['views']):
            active=lib.route_order(cfg,entries,selection)
            self.assertEqual([k for k in published if k in active],active)

    def test_file_numbers_follow_the_execution_order(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entries=lib.validate_declarations(cfg)
        numbers=[entries[k]['priority'] for k in lib.subscription_order(cfg,entries)]
        self.assertEqual(numbers,sorted(numbers))

    def test_index_has_numbered_headings_and_separate_name_columns(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entries=lib.validate_declarations(cfg)
        index=lib.render_index(cfg,entries)
        self.assertIn('## 1 网络接入与局域网',index)
        self.assertIn('### 3.1 ',index)
        self.assertIn('| 序号 | 英文名称 | 中文名称 | 用途与选择 | 订阅地址 |',index)
        for row in re.findall(r'^\| \d+ \| .+$',index,re.M):
            self.assertEqual(len(row.split('|')[1:-1]),5)
        self.assertIn('| '+priority_label(entries['claude-connections'])+' | [claude-connections]',index)

    def test_each_aggregate_has_its_own_subheading_and_table(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entries=lib.validate_declarations(cfg)
        index=lib.render_index(cfg,entries)
        sections=re.split(r'(?m)^#{2,3} ',index)
        for key in cfg['views']:
            number=priority_label(entries[key])
            with self.subTest(aggregate=key):
                section=next(s for s in sections if re.search(r'^\| '+number+r' \| ',s,re.M))
                self.assertIn('合集',section.splitlines()[0])
                self.assertEqual(re.findall(r'^\| (\d+) \| ',section,re.M),[number])
