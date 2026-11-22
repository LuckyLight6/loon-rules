import json
import unittest
from checks.source_fixtures import repository_rows

from loon_rules.rules import Invalid, read_rules
from loon_rules.generation import pipeline as library
from loon_rules.generation.pipeline import compact, ordered_route, decorate, merge_view

def recipe(name, index=0):
    entry=next(e for e in json.loads((library.ROOT/'config/catalog.json').read_text())['entries']
               if e['id']==name)
    return entry['extract'][index]


class LibraryChecks(unittest.TestCase):
    def test_current_product_and_region_anchors(self):
        c=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(c)
        data=repository_rows(library.ROOT,c)
        order=library.route_order(c,entries)
        for host,wanted in {
            'news.apple.com':'apple-news-and-sports',
            'appldnld.apple.com.edgesuite.net':'apple-update-downloads',
            'install.apps-marketplace.apple.com':'apple-store-transactions',
            'iphonesubmissions.apple.com':'apple-feedback-and-diagnostics',
            'autologon.microsoftazuread-sso.com':'microsoft-account-authentication',
            'api.passwordreset.microsoftonline.com':'microsoft-account-authentication',
            'smtp-relay.gmail.com':'google-gmail-mail',
            'myaccount.google.com':'google-account-authentication',
            'netflix.com.edgesuite.net':'netflix-video-and-delivery',
            'melogin.cn':'local-links-and-addresses',
            'tplinkrepeater.net':'local-links-and-addresses',
            'fmipmobile.icloud.com':'apple-find-my',
            'p131-fmipmobile.icloud.com':'apple-find-my',
            'data.icloud-content.com.cn':'apple-icloud-mainland',
            'data.icloud-content.com':'apple-icloud-content-domains',
        }.items():
            with self.subTest(host=host):
                self.assertEqual(ordered_route(host,order,data),wanted)

    def test_ecosystem_bundles_keep_other_views_in_charge_of_ai_and_video(self):
        from loon_rules.generation.ordering import view_selections
        c=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(c)
        self.assertIn('google-all',c['views'])
        self.assertIn('microsoft-all',c['views'])
        for selection in view_selections(c,entries,maximal=True):
            order=library.route_order(c,entries,selection)
            data={k:read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())
                  for k in order}
            for host,wanted in {
                'gemini.google.com':'ai-overseas-all',
                'copilot.cloud.microsoft':'ai-overseas-all',
                'www.youtube.com':'overseas-media-all',
                'accounts.google.com':'google-all',
                'outlook.live.com':'microsoft-all',
            }.items():
                self.assertEqual(ordered_route(host,order,data),wanted,(selection,host))

    def test_merge_does_not_treat_ip_dns_options_as_duplicates(self):
        rows=['DOMAIN,api.product.example','DOMAIN-SUFFIX,product.example',
              'IP-CIDR,192.0.2.0/24','IP-CIDR,192.0.2.0/24,no-resolve']
        self.assertEqual(compact(rows+rows),rows[1:])

    def test_compact_removes_multilabel_wildcards_only_under_a_complete_suffix(self):
        rows=['DOMAIN-WILDCARD,*.*.vm.example','DOMAIN-WILDCARD,api*.other.example',
              'DOMAIN-SUFFIX,vm.example','DOMAIN-SUFFIX,api.other.example']
        self.assertEqual(compact(rows),rows[1:])

    def test_specialty_hits_before_parent_domain(self):
        rows={'relay':['DOMAIN,mask.icloud.com'],'sync':['DOMAIN-SUFFIX,icloud.com']}
        self.assertEqual(ordered_route('mask.icloud.com',['relay','sync'],rows),'relay')
        self.assertEqual(ordered_route('file.icloud.com',['relay','sync'],rows),'sync')

    def test_earlier_shared_suffix_shadows_specialty_but_later_fallback_does_not(self):
        data={'shared':['DOMAIN-SUFFIX,delivery.example'],'video':['DOMAIN-SUFFIX,video.delivery.example']}
        entries={'shared':{'fallback':True},'video':{}}
        with self.assertRaisesRegex(Invalid,'video.*shared'):
            library.verify_domain_order(['shared','video'],entries,data)
        library.verify_domain_order(['video','shared'],entries,data)

    def test_apple_intelligence_selector_keeps_relays_out_of_general_siri_and_shared_cdn(self):
        body='<h2 id="aisirisearch">AI</h2><table>'+''.join(
            f'<tr><td>{host}</td><td>443</td><td>TCP</td><td>iOS</td><td>{scope}</td></tr>'
            for host,scope in [
                ('apple-relay.apple.com','Apple Intelligence Extensions'),
                ('cp4.cloudflare.com','Private Cloud Compute'),
                ('guzzoni.apple.com','Siri and dictation requests'),
                ('unlisted.shared.example','Shared image delivery'),
            ])+'</table>'
        self.assertEqual(library.extract_rows(recipe('apple-intelligence-relays'),body),{
            'DOMAIN,apple-relay.apple.com','DOMAIN,cp4.cloudflare.com'})

    def test_apple_intelligence_follows_new_official_relay_hosts_by_purpose(self):
        body='<h2 id="aisirisearch">AI</h2><table>'+''.join(
            f'<tr><td>{host}</td><td>443</td><td>TCP, UDP</td><td>iOS</td><td>{purpose}</td></tr>'
            for host,purpose in [
                ('pcc.new-relay.example','Private Cloud Compute'),
                ('extension.new-relay.example','Apple Intelligence Extensions'),
                ('mask.icloud.com','iCloud Private Relay'),
                ('guzzoni.apple.com','Siri and dictation requests'),
                ('images.new-relay.example','Shared image delivery'),
            ])+'</table>'
        self.assertEqual(library.extract_rows(recipe('apple-intelligence-relays'),body),{
            'DOMAIN,pcc.new-relay.example','DOMAIN,extension.new-relay.example'})

    def test_find_my_uses_the_apple_number_band_before_shared_icloud(self):
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        band=next(band for band in config['routing-bands'] if band['title']=='Apple 生态')
        self.assertEqual(band['start'],2000)
        self.assertIn('apple-find-my',band['ids'])
        order=library.route_order(config,entries)
        self.assertLess(order.index('apple-find-my'),order.index('apple-cloud-sync'))

    def test_timestamps_track_rule_body_and_not_build_time(self):
        e={'id':'store-api','description':'购物','boundary':'不含安装包','sources':['https://example.test/api']}
        now='2026-11-19T08:00:00Z'
        then='2026-11-20T08:00:00Z'
        f=decorate(e,['DOMAIN,api.example.test'],None,now)
        self.assertEqual(decorate(e,['DOMAIN,api.example.test'],f,then),f)
        g=decorate(e,['DOMAIN,api2.example.test'],f,then)
        self.assertIn('# created-at: '+now,g)
        self.assertIn('# updated-at: '+then,g)

    def test_maas_roles_are_specific_to_published_regions(self):
        body=('<h2 id="api"></h2><table><tr><td>Region</td><td>OpenAI-compatible</td>'
              '<td>Anthropic-compatible</td></tr>'
              '<tr><td>China (Beijing)</td><td>https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/v1</td>'
              '<td>https://trial.cn-beijing.maas.aliyuncs.com/v1</td></tr>'
              '<tr><td>Germany (Frankfurt)</td><td>https://trial.eu-central-1.maas.aliyuncs.com/compat</td>'
              '<td>https://dashscope-intl.aliyuncs.com/v1</td></tr></table>')
        self.assertEqual(library.extract_rows(recipe('qwen-mainland'),body),{'DOMAIN-SUFFIX,cn-beijing.maas.aliyuncs.com'})
        self.assertEqual(library.extract_rows(recipe('qwen-international'),body),
            {'DOMAIN,dashscope-intl.aliyuncs.com','DOMAIN-SUFFIX,eu-central-1.maas.aliyuncs.com'})

    def test_combined_view_only_uses_published_members(self):
        view={'id':'ai-overseas-all','members':['claude','assistant'],'exclude':['DOMAIN,shared.example']}
        data={'claude':['DOMAIN-SUFFIX,claude.ai','DOMAIN,shared.example'],
              'assistant':['DOMAIN-SUFFIX,muse.ai'],'unrelated':['DOMAIN,models.example']}
        self.assertEqual(merge_view(view,data),['DOMAIN-SUFFIX,claude.ai','DOMAIN-SUFFIX,muse.ai'])

    def test_numbered_file_and_order_share_the_same_rank(self):
        entries={k:{'id':k,'priority':p} for k,p in [('general',182),('service',61),('bundle',60)]}
        c={'detailed':['service'],'general':['general'],'views':['bundle'],'optional':[]}
        self.assertEqual(library.route_order(c,entries),['service','general'])
        self.assertEqual(library.rule_filename(entries['service']),'061-service.lsr')

    def test_domain_partition_never_imports_shared_platforms_or_keywords(self):
        rows=['DOMAIN-SUFFIX,shared.test','DOMAIN,api.service.test','DOMAIN-KEYWORD,service',
              'DOMAIN-SUFFIX,cdn.service.test','DOMAIN-SUFFIX,otherservice.test',
              'DOMAIN,ads.service.test','IP-CIDR,192.0.2.0/24,no-resolve']
        self.assertEqual(library.project_domains(rows,{'roots':['service.test'],'exclude':['ads.service.test']}),
            ['DOMAIN,api.service.test','DOMAIN-SUFFIX,cdn.service.test'])

    def test_ip_stage_does_not_use_literal_only_rows_after_dns(self):
        data={'lan':['IP-CIDR,192.0.2.0/24,no-resolve','IP-CIDR6,fc00::/7']}
        self.assertEqual(library.ordered_ip_route('192.0.2.2',['lan'],data,literal=True),'lan')
        self.assertIsNone(library.ordered_ip_route('192.0.2.2',['lan'],data,literal=False))
        self.assertEqual(library.ordered_ip_route('fd00::2',['lan'],data,literal=False),'lan')

    def test_a_dns_answer_in_ipv4_link_local_space_does_not_trigger_lan_bypass(self):
        lan='local-links-and-addresses'
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        data={lan:read_rules((library.ROOT/'rules'/library.rule_filename(entries[lan])).read_text())}
        self.assertIsNone(library.ordered_ip_route('169.254.0.2',[lan],data,literal=False))
        self.assertEqual(library.ordered_ip_route('169.254.0.2',[lan],data,literal=True),lan)

    def test_overseas_coverage_and_ip_check_hosts_use_their_own_rules(self):
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        order=library.route_order(config,entries)
        data={k:read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())
              for k in order}
        for host,expected in {
            'www.okx.com':'okx-platform',
            'www.binance.info':'binance-platform',
            'en.wikipedia.org':'overseas-sites-extra',
            '2026.ip138.com':'ip-egress-checks',
            'my.ip.cn':'ip-egress-checks',
            'myip.ipip.net':'ip-egress-checks',
            'www.ip138.com':'overseas-sites-extra',
            'www.ipip.net':'mainland-domains',
            'www.baidu.com':'baidu-shared-services',
            'chatgpt.com':'chatgpt-connections',
        }.items():
            with self.subTest(host=host):
                self.assertEqual(library.ordered_route(host,order,data),expected)

    def test_ad_rules_do_not_block_app_configuration_or_turnstile(self):
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        lists=('apple-and-ai-privacy-exceptions','general-ad-and-tracking','extended-ad-and-tracking')
        data={k:read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())
              for k in lists}
        for host in ('featuregates.org','api.statsigcdn.com','assetsconfigcdn.org',
                     'beyondwickedmapping.org','challenges.cloudflare.com','cloudflare-dns.com'):
            with self.subTest(host=host):
                self.assertIsNone(library.ordered_route(host,lists,data))

    def test_verified_hosts_route_by_service_without_enabling_compatibility_lists(self):
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        order=library.route_order(config,entries)
        data={k:read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())
              for k in order}
        for host,expected in {
            'fpinit.itunes.apple.com':'apple-store-transactions',
            'swcdn.g.aaplimg.com':'apple-update-downloads',
            'updates-http.cdn-apple.com.akadns.net':'apple-update-downloads',
            'updates-http.g.aaplimg.com':'apple-update-downloads',
            'mesu.g.aaplimg.com':'apple-update-control',
            'www.liblib.art':'liblib-mainland',
            'openapi.liblibai.cloud':'liblib-mainland',
            'qwen.ai':'qwen-international',
            'z.ai':'zhipu-international',
            'hima.auto':'huawei-shared-services',
            'www.hima.auto':'huawei-shared-services',
            'steamcommunity-a.akamaihd.net':'steam-international-platform',
            'steambroadcast.akamaized.net':'steam-international-platform',
            'dl.steam.clngaa.com':'steam-mainland-downloads',
        }.items():
            with self.subTest(host=host):
                self.assertEqual(library.ordered_route(host,order,data),expected)
        for host,owner in [
            ('unrelated.akamaized.net','steam-international-platform'),
            ('unused.liblibai.cloud','ai-cn-all'),
            ('unrelated.g.aaplimg.com','apple-update-downloads'),
        ]:
            with self.subTest(host=host):
                self.assertIsNone(library.ordered_route(host,[owner],data))

    def test_overseas_domain_merge_does_not_reintroduce_wide_direct_conflicts(self):
        entry={'merge-domains':{'include':['overseas'],'protect':['mainland']}}
        data={
            'overseas':['DOMAIN,cdn.cn.example','DOMAIN-SUFFIX,dual.example',
                        'DOMAIN-SUFFIX,restricted.example','DOMAIN,cdn.restricted.example',
                        'IP-CIDR,1.1.1.1/32,no-resolve','DOMAIN-KEYWORD,abc'],
            'mainland':['DOMAIN-SUFFIX,cn.example','DOMAIN,download.dual.example'],
        }
        self.assertEqual(library.merge_domain_sources(entry,data),['DOMAIN-SUFFIX,restricted.example'])

    def test_routine_fallbacks_leave_specialty_domains_with_their_owners(self):
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        order=library.route_order(config,entries,config.get('recommended-views',()))
        routine=[k for k in order if entries[k]['section'] in ('overseas-fallback','mainland-fallback')]
        self.assertEqual(routine,['overseas-media-extra','overseas-sites-extra','mainland-routing-all'])
        data={k:read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())
              for k in routine}
        media,web,mainland=routine
        self.assertIsNone(ordered_route('hulu.com',routine,data))
        self.assertEqual(ordered_route('dazn.com',routine,data),media)
        self.assertIsNone(ordered_route('www.okx.com',routine,data))
        self.assertIsNone(ordered_route('www.hima.auto',routine,data))
        for host in ('claude.ai','anthropic.com','chatgpt.com','www.netflix.com'):
            self.assertIsNone(ordered_route(host,[media,web],data),host)
        self.assertIsNone(ordered_route('hulu.com',[web],data))
        member_names=('mainland-domains','mainland-networks','mainland-geoip')
        expected=[row for k in member_names for row in
                  read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())]
        self.assertEqual(data[mainland],expected)
        self.assertEqual(data[mainland][-1],'GEOIP,CN')

    def test_fallback_generation_removes_complete_overlap_but_keeps_parent_of_single_host(self):
        config={'detailed':['specialty'],'general':['fallback']}
        entries={
            'specialty':{'priority':10},
            'fallback':{'priority':180,'merge-domains':{'include':['source'],'subtract-prior':True}},
        }
        data={
            'specialty':['DOMAIN,a.product.example','DOMAIN-SUFFIX,owned.example'],
            'source':['DOMAIN-SUFFIX,product.example','DOMAIN,api.owned.example'],
        }
        self.assertEqual(library.derive_domain_merges(config,entries,data),
                         {'fallback':['DOMAIN-SUFFIX,product.example']})

    def test_router_management_hosts_are_excluded_from_mainland_outputs_and_comparison_inputs(self):
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        lan='local-links-and-addresses'
        data=repository_rows(library.ROOT,config)
        for fallback in ('mainland-domains','source-xkww3n-mainland'):
            for host in ('miwifi.com','www.miwifi.com','router.miwifi.com'):
                self.assertEqual(ordered_route(host,[lan],data),lan,host)
                self.assertIsNone(ordered_route(host,[fallback],data),host)
            for host in ('www1.miwifi.com','bigota.miwifi.com'):
                self.assertIsNone(ordered_route(host,[lan],data),host)
                self.assertEqual(ordered_route(host,[fallback],data),fallback,host)

    def test_public_translation_and_protocol_addresses_are_not_lan(self):
        lan='local-links-and-addresses'
        config=json.loads((library.ROOT/'config/catalog.json').read_text())
        entries=library.validate_declarations(config)
        data={lan:read_rules((library.ROOT/'rules'/library.rule_filename(entries[lan])).read_text())}
        for address in ('64:ff9b::808:808','2002:808:808::1','2001::1','::ffff:8.8.8.8',
                        '192.0.0.9','192.0.0.10','2001:20::1'):
            for literal in (True, False):
                self.assertIsNone(library.ordered_ip_route(address,[lan],data,literal=literal),address)
        self.assertEqual(library.ordered_ip_route('192.168.31.1',[lan],data,literal=False),lan)

    def test_cross_scope_gate_checks_suffixes_on_both_sides(self):
        exact=['DOMAIN,router.vendor.example']
        parent=['DOMAIN-SUFFIX,VENDOR.example']
        self.assertTrue(library.overlapping_rules(exact,parent))
        self.assertTrue(library.overlapping_rules(parent,exact))
        self.assertFalse(library.overlapping_rules(exact,['DOMAIN,www.vendor.example']))

    def test_feed_replaces_broad_source_with_reviewed_exact_hosts(self):
        url='https://example.test/rules'
        entry={'id':'domestic','sources':[url],'kinds':['DOMAIN','DOMAIN-SUFFIX'],
               'flags':[],'excluded-rules':['DOMAIN-SUFFIX,vendor.example','DOMAIN,router.vendor.example'],
               'include':['DOMAIN,public.vendor.example']}
        downloaded={url:'DOMAIN-SUFFIX,vendor.example\nDOMAIN,router.vendor.example\nDOMAIN,another.example\n'}
        self.assertEqual(library.reviewed_input(entry,downloaded),
            ['DOMAIN,another.example','DOMAIN,public.vendor.example'])

    def test_reviewed_source_does_not_publish_arbitrary_scope_or_flag_changes(self):
        entry={'id':'source','sources':['https://example.test/rules'],
               'kinds':['DOMAIN','DOMAIN-SUFFIX','DOMAIN-KEYWORD','IP-CIDR'],
               'flags':['no-resolve'],'publish-kinds':['DOMAIN','DOMAIN-SUFFIX','IP-CIDR']}
        last=['DOMAIN-SUFFIX,product.example','IP-CIDR,192.0.2.0/24']
        downloaded={'https://example.test/rules':'DOMAIN,api.product.example\nDOMAIN,unreviewed.example\n'
                    'DOMAIN-KEYWORD,product\nIP-CIDR,192.0.2.0/24,no-resolve\n'}
        kept, review=library.refresh_reviewed_feed(entry,last,downloaded)
        self.assertEqual(kept,last)
        self.assertEqual(review,{'state':'review','new-matches':2,'missing-rules':2})
        self.assertNotIn('unreviewed.example',str(review))

    def test_reviewed_source_failure_preserves_subscribable_body(self):
        entry={'id':'source','sources':['https://example.test/rules'],'kinds':['DOMAIN'],'flags':[]}
        last=['DOMAIN,known.example']
        self.assertEqual(library.refresh_reviewed_feed(entry,last,{}),(last,{'state':'unavailable'}))

    def test_ota_payload_hosts_do_not_include_catalog_or_generic_cdn(self):
        data=recipe('apple-update-downloads')
        def hits(host,purpose='Software update downloads'):
            doc=''.join(f'<h2 id="{sec}"></h2><table><tr><td>{host}</td><td>443</td>'
                f'<td>TCP</td><td>OS</td><td>{purpose}</td></tr></table>' for sec in data['sections'])
            return bool(library.extract_rows(data,doc))
        for host in ('swcdn.apple.com','appldnld.apple.com','updates.cdn-apple.com','new-payload.apple.com'):
            self.assertTrue(hits(host),host)
        for host in ('cdn-apple.com','apple.com',
                     'swcdn.apple.com.unrelated.invalid'):
            self.assertFalse(hits(host),host)
        for host in ('mesu.apple.com','swscan.apple.com','not-swcdn.apple.com'):
            self.assertFalse(hits(host,'Software update catalog'),host)
