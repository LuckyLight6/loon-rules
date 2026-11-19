import json
import unittest

from maintain import Invalid, read_rules
import library
from library import compact, ordered_route, decorate, regional_workspaces, merge_view

class LibraryChecks(unittest.TestCase):
    def test_current_product_and_region_anchors(self):
        c=json.loads((library.ROOT/'catalog.json').read_text())
        entries=library.validate_declarations(c)
        data={k:read_rules((library.ROOT/'rules'/library.rule_filename(e)).read_text())
              for k,e in entries.items()}
        order=library.route_order(c,entries)
        for host,wanted in {
            'news.apple.com':'apple-news-and-sports',
            'appldnld.apple.com.edgesuite.net':'apple-update-downloads',
            'install.apps-marketplace.apple.com':'apple-store-transactions',
            'iphonesubmissions.apple.com':'apple-system-connectivity',
            'autologon.microsoftazuread-sso.com':'microsoft-account-authentication',
            'api.passwordreset.microsoftonline.com':'microsoft-account-authentication',
            'smtp-relay.gmail.com':'google-gmail-mail',
            'myaccount.google.com':'google-account-authentication',
            'netflix.com.edgesuite.net':'netflix-video-and-delivery',
            'melogin.cn':'local-links-and-addresses',
            'tplinkrepeater.net':'local-links-and-addresses',
            'fmipmobile.icloud.com':'apple-location-services',
            'p131-fmipmobile.icloud.com':'apple-location-services',
            'data.icloud-content.com.cn':'apple-icloud-mainland',
            'data.icloud-content.com':'apple-icloud-content-domains',
        }.items():
            with self.subTest(host=host):
                self.assertEqual(ordered_route(host,order,data),wanted)

    def test_ecosystem_bundles_keep_other_views_in_charge_of_ai_and_video(self):
        c=json.loads((library.ROOT/'catalog.json').read_text())
        entries=library.validate_declarations(c)
        self.assertIn('google-all',c['views'])
        self.assertIn('microsoft-all',c['views'])
        order=library.route_order(c,entries,c['views'])
        data={k:read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())
              for k in order}
        for host,wanted in {
            'gemini.google.com':'ai-overseas-all',
            'copilot.cloud.microsoft':'ai-overseas-all',
            'www.youtube.com':'overseas-media-all',
            'accounts.google.com':'google-all',
            'outlook.live.com':'microsoft-all',
        }.items():
            self.assertEqual(ordered_route(host,order,data),wanted,host)

    def test_merge_does_not_treat_ip_dns_options_as_duplicates(self):
        rows=['DOMAIN,api.product.example','DOMAIN-SUFFIX,product.example',
              'IP-CIDR,192.0.2.0/24','IP-CIDR,192.0.2.0/24,no-resolve']
        self.assertEqual(compact(rows+rows),rows[1:])

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
                ('unlisted.shared.example','Private Cloud Compute'),
            ])+'</table>'
        self.assertEqual(library.apple_intelligence_hosts(body),{
            'DOMAIN,apple-relay.apple.com','DOMAIN,cp4.cloudflare.com'})

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
        body=('https://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/v1 '
              'https://trial.eu-central-1.maas.aliyuncs.com/compat '
              'https://dashscope-intl.aliyuncs.com '
              'https://other.maas.aliyuncs.com https://x.cn-beijing.maas.aliyuncs.com.test')
        self.assertEqual(regional_workspaces(body,False),{'DOMAIN-SUFFIX,cn-beijing.maas.aliyuncs.com'})
        self.assertEqual(regional_workspaces(body,True),
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

    def test_router_management_hosts_have_one_owner_with_either_mainland_feed(self):
        config=json.loads((library.ROOT/'catalog.json').read_text())
        entries=library.validate_declarations(config)
        lan='local-links-and-addresses'
        for fallback in ('mainland-domain-families','mainland-service-domains'):
            data={k:read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text())
                  for k in (lan,fallback)}
            for host in ('miwifi.com','www.miwifi.com','router.miwifi.com'):
                self.assertEqual(ordered_route(host,[lan],data),lan,host)
                self.assertIsNone(ordered_route(host,[fallback],data),host)
            for host in ('www1.miwifi.com','bigota.miwifi.com'):
                self.assertIsNone(ordered_route(host,[lan],data),host)
                self.assertEqual(ordered_route(host,[fallback],data),fallback,host)

    def test_public_translation_and_protocol_addresses_are_not_lan(self):
        lan='local-links-and-addresses'
        data={lan:read_rules((library.ROOT/'rules'/'011-local-links-and-addresses.lsr').read_text())}
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
        for host in ('swcdn.apple.com','appldnld.apple.com.akadns.net','updates.cdn-apple.com'):
            self.assertTrue(library.ota_payload_host(host),host)
        for host in ('mesu.apple.com','swscan.apple.com','not-swcdn.apple.com','cdn-apple.com',
                     'swcdn.apple.com.unrelated.invalid'):
            self.assertFalse(library.ota_payload_host(host),host)
