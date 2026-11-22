import json
import unittest
from pathlib import Path

from loon_rules.generation import pipeline as lib
from checks.source_fixtures import repository_rows


class ProductCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((lib.ROOT/'config/catalog.json').read_text())
        cls.entries=lib.validate_declarations(cls.config)
        cls.data=repository_rows(lib.ROOT,cls.config)

    def test_mainland_and_international_ai_are_unions_of_products(self):
        for family in ('ai-cn-all','ai-cn-international-all'):
            with self.subTest(family=family):
                entry=self.entries[family]
                self.assertEqual(entry['mode'],'view')
                members=[r for k in entry['members'] for r in self.data[k]]
                self.assertEqual(len(members),len(set(members)))
                self.assertEqual(set(self.data[family]),set(members))

    def test_named_products_are_in_their_business_sections(self):
        expected={'gitlab-hosting':'development','docker-hub':'development',
                  'gitee-hosting':'development','stripe-payments':'payments',
                  'binance-platform':'crypto','okx-platform':'crypto',
                  'signal-messenger':'social','iqiyi-mainland':'media',
                  'playstation-network':'games','microsoft-vscode':'microsoft',
                  'apple-podcasts':'apple','google-scholar':'google',
                  'qwen-mainland':'ai','qwen-international':'ai'}
        for key,section in expected.items():
            with self.subTest(key=key):
                self.assertEqual(self.entries[key]['section'],section)

    def test_new_products_work_in_the_regular_routing_selection(self):
        order=lib.route_order(self.config,self.entries)
        for host,key in {'repo.maven.apache.org':'maven-central',
                         'registry-1.docker.io':'docker-hub',
                         'registry.npmmirror.com':'npmmirror-registry',
                         'api.deepseek.com':'deepseek-mainland',
                         'qwen.ai':'qwen-international',
                         'www.qianwen.com':'qwen-mainland',
                         'www.binance.info':'binance-platform',
                         'www.okx.com':'okx-platform',
                         'www.qualcomm.cn':'qualcomm-mainland',
                         'www.nvidia.cn':'nvidia-mainland',
                         'cn.download.nvidia.com':'nvidia-mainland',
                         'www.intel.cn':'intel-mainland',
                         'music.163.com':'netease-music',
                         'music.126.net':'netease-music',
                         'www.cloudflare.com':'cloudflare-shared-services',
                         'one.one.one.one':'cloudflare-public-dns'}.items():
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,order,self.data),key)

    def test_company_region_and_music_rules_do_not_claim_other_products(self):
        for host,key in {'www.qualcomm.com':'qualcomm-mainland',
                         'www.nvidia.com':'nvidia-mainland',
                         'www.intel.com':'intel-mainland',
                         'mail.163.com':'netease-music',
                         'tenant.163yun.com':'netease-music',
                         'web.whatsapp-plus.info':'whatsapp-messaging',
                         'tenant.workers.dev':'chatgpt-connections'}.items():
            with self.subTest(host=host):
                self.assertIsNone(lib.ordered_route(host,[key],self.data))

    def test_no_resolve_variant_preserves_names_and_literal_address_coverage(self):
        regular=self.data['local-links-and-addresses']
        without_dns=self.data['local-no-resolve-alt']
        self.assertEqual([r for r in regular if not r.startswith(('IP-CIDR,','IP-CIDR6,'))],
                         [r for r in without_dns if not r.startswith(('IP-CIDR,','IP-CIDR6,'))])
        for address in ('127.0.0.1','10.1.2.3','100.64.1.1','192.168.1.1','172.16.2.1','fd00::1','169.254.1.1'):
            with self.subTest(address=address):
                self.assertIsNotNone(lib.ordered_ip_route(address,['local-links-and-addresses'],self.data,literal=True))
                self.assertIsNotNone(lib.ordered_ip_route(address,['local-no-resolve-alt'],self.data,literal=True))
                self.assertIsNone(lib.ordered_ip_route(address,['local-no-resolve-alt'],self.data,literal=False))
        self.assertEqual(lib.ordered_ip_route('10.1.2.3',['local-links-and-addresses'],self.data,literal=False),
                         'local-links-and-addresses')

    def test_sovereign_cloud_controls_keep_their_region_in_fine_and_bundle_modes(self):
        china='microsoft-china-cloud-controls'
        for host in ('login.chinacloudapi.cn','management.chinacloudapi.cn',
                     'management.core.chinacloudapi.cn','portal.azure.cn',
                     'microsoftgraph.chinacloudapi.cn','gallery.chinacloudapi.cn'):
            with self.subTest(host=host):
                for views in ([],['microsoft-all'],['microsoft-all','multinational-mainland-all']):
                    order=lib.route_order(self.config,self.entries,views)
                    expected='multinational-mainland-all' if len(views)==2 else china
                    self.assertEqual(lib.ordered_route(host,order,self.data),expected)
        for host in ('login.microsoftonline.com','tenant.blob.core.chinacloudapi.cn'):
            self.assertIsNone(lib.ordered_route(host,[china],self.data))

    def test_social_rules_cover_real_services_without_claiming_brand_lookalikes(self):
        order=lib.route_order(self.config,self.entries)
        for host,owner in {'instagr.am':'instagram-social','graph.instagram.com':'instagram-social',
                           'www.messenger.com':'meta-shared-services','fbcdn.net':'meta-shared-services',
                           'metaaiusercontent.com':'meta-ai-assistant'}.items():
            self.assertEqual(lib.ordered_route(host,order,self.data),owner)
        for host in ('achat-followers-instagram.com','theinstagramhack.com','buyingfacebooklikes.com'):
            self.assertIsNone(lib.ordered_route(host,['instagram-social','meta-shared-services'],self.data))

    def test_ecosystem_aggregates_include_new_named_products(self):
        expected={'apple-all':['apple-podcasts','apple-developer-portal'],
                  'google-all':['google-scholar'],
                  'microsoft-all':['microsoft-vscode','microsoft-power-bi'],
                  'ai-overseas-all':['jetbrains-ai'],
                  'overseas-media-all':['hbo-streaming','bbc-news-and-video']}
        for view,members in expected.items():
            with self.subTest(view=view):
                self.assertTrue(set(members)<=set(self.entries[view]['members']))
