"""Regressions for source precedence, product coverage, and Apple role separation."""
import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples, prepare_workspace, repository_rows
from loon_rules.generation import pipeline as lib


class SharedEndpointOwners(unittest.TestCase):
    def test_later_general_vendor_fallback_preserves_product_and_shared_boundaries(self):
        from loon_rules.generation import contracts
        contract={'id':'vendor','routes':{'product':['api.vendor.example']},
                  'shared':{'*.vendor.example':'Several services share this vendor namespace'},
                  'guard-sections':['ecosystem']}
        entries={'product':{'section':'ecosystem'},
                 'general':{'section':'ecosystem','fallback':True}}
        data={'product':['DOMAIN,api.vendor.example'],
              'general':['DOMAIN-SUFFIX,vendor.example']}
        try:
            contracts.verify_routes([contract],entries,['product','general'],data)
        except lib.rules.Invalid as error:
            self.fail('后置通用层不应被当成具体产品：'+str(error))
        with self.assertRaises(lib.rules.Invalid):
            contracts.verify_routes([contract],entries,['general','product'],data)
        data['product']=['DOMAIN-SUFFIX,vendor.example']
        with self.assertRaises(lib.rules.Invalid):
            contracts.verify_routes([contract],entries,['product','general'],data)


class OfficialInputEvolution(PublicSourceExamples):
    def test_registered_provider_api_changes_follow_typed_fields_not_notes(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entry=next((e for e in cfg['entries'] if e['id']=='kilo-connections'),None)
        self.assertTrue(entry is not None,'缺少按提供商配置维护的 Kilo 产品')
        doc={'kilo':{'id':'kilo','api':'https://next-api.vendor.example/v1',
                     'doc':'https://kilo.ai/docs','note':'https://unrelated.example/secret'}}
        data={source:json.dumps(doc) for source in entry['sources']}
        actual=lib.compile_entry(entry,data)
        self.assertIn('DOMAIN,next-api.vendor.example',actual)
        self.assertNotIn('DOMAIN,unrelated.example',actual)
    def test_domain_allowlist_accepts_new_purposes_and_skips_non_endpoint_bullets(self):
        recipe={'format':'purpose-domain-lists','labels':['Required service hosts'],
                'item-separator-required':True}
        body='<p>Required service hosts</p><ul><li>login.vendor.example: Login</li>'+\
             '<li>session.next-vendor.example: New session capabilities</li>'+\
             '<li>The CLI stores credentials in a local file</li></ul>'
        try:
            actual=lib.extract_rows(recipe,body)
        except lib.rules.Invalid as error:
            self.fail('合法服务清单被非端点说明阻断：'+str(error))
        self.assertEqual(actual,{'DOMAIN,login.vendor.example','DOMAIN,session.next-vendor.example'})

    def test_new_fireworks_api_host_is_read_from_official_examples(self):
        entry=next(e for e in json.loads((lib.ROOT/'config/catalog.json').read_text())['entries']
                   if e['id']=='fireworks-model-services')
        body='See https://docs.fireworks.ai/\n\n```python\nclient = Client(base_url="https://next-api.vendor.example/v2")\n```\n'
        inputs={recipe['source']:body for recipe in entry['extract']}
        actual=lib.compile_entry(entry,inputs)
        self.assertIn('DOMAIN,next-api.vendor.example',actual)

    def test_older_cached_suffix_list_cannot_reopen_a_new_private_suffix(self):
        from loon_rules import domains
        self.assertTrue(hasattr(domains,'select_list'),'缺少公共后缀版本单向更新保护')
        template='''// VERSION: {version}
// ===BEGIN ICANN DOMAINS===
com
co.uk
// ===END ICANN DOMAINS===
// ===BEGIN PRIVATE DOMAINS===
github.io
{private}
// ===END PRIVATE DOMAINS===
'''
        old=template.format(version='2026-11-20_10-00-00_UTC',private='')
        current=template.format(version='2026-11-21_10-00-00_UTC',private='hosting.vendor.com')
        selected,state=domains.select_list(old,current)
        self.assertEqual(domains.Suffixes(selected).suffix('tenant.hosting.vendor.com'),('hosting.vendor.com',True))
        self.assertEqual(state['state'],'retained-newer')
        selected,state=domains.select_list(current,old)
        self.assertEqual(selected,current)
        self.assertEqual(state['state'],'current')


class FallbackSourcePriority(PublicSourceExamples):
    def test_subdomain_reservation_does_not_claim_the_bare_vendor_site(self):
        from loon_rules.generation.membership import outside_domain_scopes
        rows=['DOMAIN-SUFFIX,vendor.example','DOMAIN,vendor.example','DOMAIN,api.vendor.example']
        try:actual=outside_domain_scopes(rows,['DOMAIN-WILDCARD,*.vendor.example'])
        except lib.rules.Invalid as error:self.fail('合法子域预留无法参与去重：'+str(error))
        self.assertEqual(actual,['DOMAIN,vendor.example'])

    def test_two_refreshes_keep_restricted_routes_and_remove_duplicate_domestic_rows(self):
        overseas='https://rules.vendor.example/restricted.list'
        mainland='https://rules.vendor.example/mainland.list'
        component={'id':'source-gfw','mode':'managed','policy-hint':'global',
                   'description':'受限来源','boundary':'只供生成器使用','sources':[overseas],
                   'kinds':['DOMAIN-SUFFIX'],'flags':[],'license':'MIT'}
        foreign={'id':'foreign','mode':'compiled','priority':675,'section':'overseas',
                 'description':'海外补充','boundary':'专项之后，国内补充之前','sources':[overseas],
                 'merge-domains':{'include':['source-gfw'],'protect':['domestic'],
                                  'prefer':['source-gfw'],'subtract-prior':True},'fallback':True}
        domestic={'id':'domestic','mode':'managed','priority':704,'section':'mainland',
                  'description':'国内补充','boundary':'国内共用范围','sources':[mainland],
                  'kinds':['DOMAIN-SUFFIX'],'flags':[],'license':'MIT',
                  'policy-hint':'domestic','domain-remainder':True,'fallback':True}
        cfg={'schema-version':2,'entries':[foreign,domestic],'source-components':[component],
             'sections':[{'id':'overseas','title':'海外'},{'id':'mainland','title':'国内'}],
             'critical':{'www.blocked.example':['foreign'],'www.china.example':['domestic']},
             'shared-negatives':[]}
        foreign_rows=['DOMAIN-SUFFIX,blocked.example','DOMAIN-SUFFIX,other.example']
        domestic_rows=['DOMAIN-SUFFIX,blocked.example','DOMAIN-SUFFIX,china.example']
        inputs={overseas:'\n'.join(foreign_rows),mainland:'\n'.join(domestic_rows)}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),\
                patch.object(lib.transport,'download',side_effect=inputs.__getitem__),redirect_stdout(StringIO()):
            root=Path(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            (root/'data/maintenance-state.json').write_text(json.dumps({
                'component-rules':{'source-gfw':foreign_rows}}))
            for entry,rows in [(foreign,foreign_rows),(domestic,domestic_rows)]:
                (root/'rules'/lib.rule_filename(entry)).write_text(
                    lib.decorate(entry,rows,None,'2026-01-01T00:00:00Z'))
            for _ in range(2):
                self.assertEqual(lib.run(),0)
                actual=repository_rows(root,cfg)
                self.assertEqual(lib.ordered_route('www.blocked.example',lib.route_order(cfg,entries),actual),'foreign')
                self.assertEqual(actual['domestic'],['DOMAIN-SUFFIX,china.example'])
            self.assertEqual(lib.run(offline=True),0)

    def test_declared_split_preserves_the_whole_service_and_its_source(self):
        from loon_rules.sources import coverage
        source='https://vendor.example/network'
        entries={'common':{'mode':'compiled','priority':229,'section':'apple','sources':[source]},
                 'specific':{'mode':'compiled','priority':231,'section':'apple','sources':[source],
                             'separates':['common']}}
        previous={'common':['DOMAIN-SUFFIX,service.vendor.example']}
        data={'common':['DOMAIN,other.vendor.example'],
              'specific':['DOMAIN-SUFFIX,service.vendor.example']}
        proof=coverage.reassignments(entries,previous,data,selected={},order=list(entries))
        self.assertEqual(proof,{'common':{'DOMAIN-SUFFIX,service.vendor.example':
                         {'owner':'specific','sources':[source]}}})
        data['specific']=['DOMAIN,service.vendor.example']
        self.assertEqual(coverage.reassignments(entries,previous,data,selected={},order=list(entries)),{})
        entries['specific']['sources']=['https://different.example/network']
        data['specific']=['DOMAIN-SUFFIX,service.vendor.example']
        self.assertEqual(coverage.reassignments(entries,previous,data,selected={},order=list(entries)),{})

    def test_restricted_source_survives_broad_domestic_conflict(self):
        entry={'merge-domains':{'include':['ordinary','restricted'],
                               'protect':['mainland'],'prefer':['restricted']}}
        data={'ordinary':['DOMAIN-SUFFIX,ordinary.example'],
              'restricted':['DOMAIN-SUFFIX,blocked.example'],
              'mainland':['DOMAIN-SUFFIX,ordinary.example','DOMAIN-SUFFIX,blocked.example']}
        self.assertEqual(lib.merge_domain_sources(entry,data),['DOMAIN-SUFFIX,blocked.example'])

    def test_specific_domestic_product_keeps_priority_over_restricted_parent(self):
        cfg={'detailed':['china-product'],'general':['foreign']}
        entries={'china-product':{'priority':500},
                 'foreign':{'priority':675,'merge-domains':{
                     'include':['restricted'],'protect':['mainland'],
                     'prefer':['restricted'],'subtract-prior':True}}}
        data={'china-product':['DOMAIN-SUFFIX,cn.vendor.example'],
              'restricted':['DOMAIN-SUFFIX,vendor.example','DOMAIN,unrelated.example'],
              'mainland':['DOMAIN-SUFFIX,vendor.example']}
        data.update(lib.derive_domain_merges(cfg,entries,data))
        order=lib.route_order(cfg,entries)
        self.assertEqual(lib.ordered_route('api.cn.vendor.example',order,data),'china-product')
        self.assertEqual(lib.ordered_route('www.vendor.example',order,data),'foreign')

    def test_preferred_source_must_be_an_included_input(self):
        component={'id':'source','mode':'managed','description':'来源','boundary':'测试输入',
                   'sources':['https://rules.vendor.example/list'],'kinds':['DOMAIN'],
                   'flags':[],'license':'MIT'}
        entry={'id':'foreign','mode':'compiled','priority':675,'section':'overseas',
               'description':'海外补充','boundary':'按来源选路','sources':component['sources'],
               'merge-domains':{'include':['source'],'prefer':['not-in-this-merge']}}
        cfg={'schema-version':2,'entries':[entry],'source-components':[component],
             'sections':[{'id':'overseas','title':'海外'}],'critical':{},'shared-negatives':[]}
        with self.assertRaisesRegex(lib.rules.Invalid,'优先来源'):
            lib.validate_declarations(cfg)


class PublishedRepairRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=json.loads((lib.ROOT/'config/catalog.json').read_text())
        cls.entries=lib.validate_declarations(cls.config)
        cls.data=repository_rows(lib.ROOT,cls.config)
        cls.order=lib.route_order(cls.config,cls.entries)

    def test_both_grandslam_hosts_use_the_account_route_in_detail_and_aggregate(self):
        for host in ('gsa.apple.com','gsas.apple.com'):
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),'apple-account-authentication')
                self.assertEqual(lib.ordered_route(host,['apple-all'],self.data),'apple-all')

    def test_store_search_is_recognized_before_ip_fallback_and_images_keep_the_cdn_route(self):
        self.assertEqual(lib.ordered_route('search.itunes.apple.com',self.order,self.data),
                         'apple-store-transactions')
        self.assertEqual(lib.ordered_route('is1-ssl.mzstatic.com',self.order,self.data),
                         'apple-shared-store-assets')

    def test_apple_web_and_unclassified_services_do_not_fall_through_to_domestic_ips(self):
        for host in ('www.apple.com','support.apple.com','privacy.apple.com'):
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),'apple-other-services')
        expected={'gsa.apple.com':'apple-account-authentication',
                  'account.apple.com':'apple-account-authentication',
                  'search.itunes.apple.com':'apple-store-transactions',
                  'is1-ssl.mzstatic.com':'apple-shared-store-assets',
                  'time.apple.com':'apple-system-connectivity',
                  'content.icloud-content.com':'apple-icloud-content-domains',
                  'www.icloud.com':'apple-cloud-sync'}
        for host,owner in expected.items():
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),owner)

    def test_safe_browsing_is_a_google_security_api_instead_of_an_advertising_target(self):
        for host in ('safebrowsing.googleapis.com','safebrowsing.googleapis-cn.com'):
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),'google-platform-services')
                self.assertEqual(lib.ordered_route(host,
                                 lib.route_order(self.config,self.entries,['google-all']),self.data),'google-all')
        self.assertEqual(lib.ordered_route('safebrowsing.urlsec.qq.com',self.order,self.data),
                         'mainland-domains')

    def test_apple_aggregate_keeps_independent_certificate_and_general_fallback_routes(self):
        order=lib.route_order(self.config,self.entries,['apple-all'])
        expected={'www.apple.com':'apple-other-services',
                  'ocsp.apple.com':'apple-certificate-validation',
                  'account.apple.com':'apple-all'}
        for host,owner in expected.items():
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,order,self.data),owner)

    def test_icloud_account_controls_follow_numeric_shards(self):
        for host in ('p181-acsegateway.icloud.com', 'p181-mcc.icloud.com', 'p181-quota.icloud.com',
                     'p48-acsegateway.icloud.com', 'p47-mcc.icloud.com', 'p05-quota.icloud.com'):
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),'apple-account-authentication')

    def test_icloud_account_routing_excludes_content_and_unconfirmed_names(self):
        expected = {
            'p181-mccgateway.icloud.com': 'apple-cloud-sync',
            'p181-docws.icloud.com': 'apple-cloud-sync',
            'p181-ckdatabasews.icloud.com': 'apple-cloud-sync',
            'gatewayws.icloud.com': 'apple-cloud-sync',
            'pX1-mcc.icloud.com': 'apple-cloud-sync',
            'p181-acsegateway.icloud.com.cn': 'apple-icloud-mainland',
            'p181-content.icloud-content.com': 'apple-icloud-content-domains',
        }
        for host, owner in expected.items():
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),owner)

    def test_device_registration_is_separate_from_esim_time_and_management(self):
        expected={'albert.apple.com':'apple-device-registration',
                  'identity.apple.com':'apple-device-registration',
                  'sq-device.apple.com':'apple-system-connectivity',
                  'time-ios.apple.com':'apple-system-connectivity',
                  'deviceenrollment.apple.com':'apple-system-connectivity'}
        for host,owner in expected.items():
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),owner)

    def test_find_my_is_separate_from_location_and_icloud_file_transfer(self):
        expected={'fmipmobile.icloud.com':'apple-find-my',
                  'p131-fmipmobile.icloud.com':'apple-find-my',
                  'fmfmobile.icloud.com':'apple-find-my',
                  'gsp9-ssl.apple.com':'apple-location-services',
                  'content.icloud-content.com':'apple-icloud-content-domains',
                  'www.icloud.com':'apple-cloud-sync'}
        for host,owner in expected.items():
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),owner)

    def test_feedback_uploads_do_not_share_the_update_control_table(self):
        for host in ('cssubmissions.apple.com','fba.apple.com','iphonesubmissions.apple.com'):
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),
                                 'apple-feedback-and-diagnostics')
        self.assertEqual(lib.ordered_route('gs.apple.com',self.order,self.data),
                         'apple-update-control')

    def test_restored_ai_products_have_product_owners_and_join_the_overseas_union(self):
        for host,owner in {'ampcode.com':'amp-connections',
                           'anythingllm.com':'anythingllm-connections',
                           'api.fireworks.ai':'fireworks-model-services'}.items():
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),owner)
                self.assertEqual(lib.ordered_route(host,['ai-overseas-all'],self.data),
                                 'ai-overseas-all')

    def test_international_iqiyi_is_not_captured_by_the_mainland_parent(self):
        for host in ('iq.com','intl.iqiyi.com','intl-subscription.iqiyi.com','intl-rcd.iqiyi.com'):
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),'iqiyi-international')
        self.assertEqual(lib.ordered_route('www.iqiyi.com',self.order,self.data),'iqiyi-mainland')

    def test_gfw_membership_precedes_general_domestic_supplement(self):
        for host in ('apache.org','nssurge.com','weather.com'):
            with self.subTest(host=host):
                self.assertEqual(lib.ordered_route(host,self.order,self.data),'overseas-sites-extra')
        self.assertEqual(lib.ordered_route('api.deepseek.com',self.order,self.data),
                         'deepseek-mainland')

    def test_provider_regions_do_not_collapse_into_a_shared_mainland_suffix(self):
        registry={key:{'id':key,'api':url} for key,url in {
            'stepfun-ai':'https://api.stepfun.ai/v1',
            'stepfun-ai-step-plan':'https://api.stepfun.ai/step_plan/v1',
            'xiaomi-token-plan-ams':'https://token-plan-ams.xiaomimimo.com/v1',
            'xiaomi-token-plan-sgp':'https://token-plan-sgp.xiaomimimo.com/v1',
            'xiaomi-token-plan-cn':'https://token-plan-cn.xiaomimimo.com/v1',
            'xiaomi':'https://api.xiaomimimo.com/v1',
            'modelscope':'https://api-inference.modelscope.cn/v1'}.items()}
        source='https://models.dev/api.json';data={key:[] for key in self.entries}
        for key in ['stepfun-international','xiaomi-international','xiaomi-mainland-and-shared','modelscope-mainland']:
            data[key]=lib.compile_entry(self.entries[key],{source:json.dumps(registry)})
        data['mainland-domains']=['DOMAIN-SUFFIX,xiaomimimo.com']
        expected={'api.stepfun.ai':'stepfun-international',
                  'token-plan-ams.xiaomimimo.com':'xiaomi-international',
                  'token-plan-sgp.xiaomimimo.com':'xiaomi-international',
                  'token-plan-cn.xiaomimimo.com':'xiaomi-mainland-and-shared',
                  'api.xiaomimimo.com':'xiaomi-mainland-and-shared',
                  'api-inference.modelscope.cn':'modelscope-mainland'}
        for host,owner in expected.items():
            with self.subTest(host=host):self.assertEqual(lib.ordered_route(host,self.order,data),owner)

    def test_official_role_updates_add_new_activation_hosts_without_new_literals(self):
        self.assertTrue('apple-device-registration' in self.entries,'缺少设备激活与证书登记专表')
        entry=self.entries['apple-device-registration']
        body='<h2 id="devicesetup">Device setup</h2><table>'+''.join(
            '<tr>'+''.join('<td>'+value+'</td>' for value in row)+'</tr>'
            for row in [('activation-next.apple.com','443','TCP','iOS','Device activation','Yes'),
                        ('esim-next.apple.com','443','TCP','iOS','eSIM activation','—'),
                        ('clock-next.apple.com','123','UDP','iOS','Used by devices to set their date and time','—')])+'</table>'
        body+='<h2 id="devicemanagement">Device management</h2><table><tr>'+''.join(
            '<td>'+value+'</td>' for value in ('certificate-next.apple.com','443','TCP','iOS',
                                               'APNs certificate request portal','Yes'))+'</tr></table>'
        result=set().union(*(lib.extract_rows(recipe,body) for recipe in entry['extract']))
        self.assertEqual(result,{'DOMAIN,activation-next.apple.com','DOMAIN,certificate-next.apple.com'})
