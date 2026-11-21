import unittest
import json
from loon_rules.generation import pipeline as library
from loon_rules.sources.inputs import extract_rows

from loon_rules.rules import Invalid, read_rules, first_policy, verify_routes
from loon_rules.rules import ip_options, verify_ip_options


class RuleContracts(unittest.TestCase):
    def test_coverage_guard_uses_the_same_wildcard_scope_as_request_matching(self):
        wildcard='DOMAIN-WILDCARD,*.vendor.example'
        for previous in (['DOMAIN,smtp.vendor.example'],['DOMAIN-SUFFIX,mail.vendor.example'],
                         ['DOMAIN-WILDCARD,p??.vendor.example']):
            library.guard_coverage('product',previous,[wildcard])
            self.assertEqual(library.uncovered_count(previous,[wildcard]),0)
        with self.assertRaises(Invalid):library.guard_coverage('product',['DOMAIN,vendor.example'],[wildcard])
        with self.assertRaises(Invalid):library.guard_coverage('product',['DOMAIN,p001.vendor.example'],
                                      ['DOMAIN-WILDCARD,p??.vendor.example'])
        library.guard_coverage('product',['DOMAIN,p01.vendor.example'],['DOMAIN-WILDCARD,p??.vendor.example'])
        library.guard_coverage('product',[wildcard],['DOMAIN-SUFFIX,vendor.example'])
        self.assertTrue(library.overlapping_rules(['DOMAIN,smtp.vendor.example'],[wildcard]))
        self.assertFalse(library.overlapping_rules(['DOMAIN,vendor.example'],[wildcard]))

    def test_invalid_body_or_arbitrary_policy_is_not_a_rules_release(self):
        for body in ('<html>blocked</html>', '[Plugin]\nhttps://example.test/', 'DOMAIN,example.test,DIRECT',
                     'IP-CIDR,17.0.0.0/96', 'DOMAIN-SUFFIX,example.test\nFINAL,DIRECT'):
            with self.subTest(body=body), self.assertRaises(Invalid):
                read_rules(body, {'DOMAIN', 'DOMAIN-SUFFIX', 'IP-CIDR'})

    def test_compilation_checks_real_scope_before_replacing_a_subscription(self):
        before=['DOMAIN,api.example.test','DOMAIN,a.example.test']
        entry={'id':'product','projection':[{'source':'source','roots':['example.test']}]}
        for rows,ok in [(before+['DOMAIN,b.example.test'],True),(['DOMAIN,b.example.test'],False)]:
            now=library.compile_entry(entry,{'source':'\n'.join(rows)})
            if ok: library.guard_coverage('product',before,now)
            else:
                with self.assertRaises(Invalid): library.guard_coverage('product',before,now)

    def test_ordinary_source_cannot_publish_a_new_broad_rule(self):
        entry={'id':'feed','sources':['source'],'kinds':['DOMAIN','DOMAIN-SUFFIX','IP-CIDR','IP-CIDR6'],'flags':[]}
        old=['DOMAIN,api.example.test']
        for line in ('DOMAIN-SUFFIX,com','DOMAIN-SUFFIX,apple.com','IP-CIDR,16.0.0.0/7','IP-CIDR6,2600::/12'):
            kept,_=library.refresh_reviewed_feed(entry,old,{'source':'\n'.join(old+[line])})
            self.assertEqual(kept,old,line)

    def test_removed_address_or_changed_dns_mode_is_not_silently_accepted(self):
        bare='IP-CIDR,10.0.0.0/8'
        only='IP-CIDR,169.254.0.0/16'
        e={'id':'mixed','ip-match':'per-rule','literal_ips':[only],'dns_required':[bare]}
        for rows in ([only+',no-resolve'],[only+',no-resolve',bare+',no-resolve']):
            with self.assertRaisesRegex(Invalid,'IP 匹配'): verify_ip_options(e,ip_options(rows))

    def test_a_published_ip_scope_cannot_silently_change_dns_intent(self):
        key='IP-CIDR,192.0.2.0/24'
        for intent,correct,wrong in (
            ('target-ip',key+',no-resolve',key),
            ('allow-dns',key,key+',no-resolve'),
        ):
            with self.subTest(intent=intent):
                entry={'id':'network','ip-match':intent}
                verify_ip_options(entry,ip_options([correct]))
                with self.assertRaisesRegex(Invalid,'IP 匹配'):
                    verify_ip_options(entry,ip_options([wrong]))

    def test_a_mixed_scope_must_declare_every_ip_row(self):
        special='IP-CIDR,192.0.2.0/24'
        lan='IP-CIDR,192.168.0.0/16'
        undeclared='IP-CIDR,198.18.0.0/15'
        entry={'id':'mixed','ip-match':'per-rule','literal_ips':[special],'dns_required':[lan]}
        rows=[special+',no-resolve',lan]
        verify_ip_options(entry,ip_options(rows))
        with self.assertRaisesRegex(Invalid,'198.18.0.0/15'):
            verify_ip_options(entry,ip_options(rows+[undeclared]))

    def test_published_rules_reject_missing_intent_and_conflicting_view_members(self):
        address='IP-CIDR,192.0.2.0/24'
        with self.assertRaisesRegex(Invalid,'须先声明'):
            verify_ip_options({'id':'network'},ip_options([address]),complete=True)
        view={'id':'combined','mode':'view'}
        verify_ip_options(view,ip_options([address]),complete=True)
        with self.assertRaisesRegex(Invalid,'合集成员不一致'):
            verify_ip_options(view,ip_options([address,address+',no-resolve']),complete=True)

    def test_satisfied_service_samples_do_not_excuse_matching_shared_domains(self):
        positive = {'gemini.google.com':'Gemini'}
        bounds = [{'hosts':['storage.googleapis.com'], 'forbid':['Gemini']}]
        good = [('Gemini',['DOMAIN,gemini.google.com']),('Global',['DOMAIN-SUFFIX,googleapis.com'])]
        verify_routes(good,positive,bounds)
        bad = [('Gemini',['DOMAIN,gemini.google.com','DOMAIN-SUFFIX,googleapis.com']),good[-1]]
        with self.assertRaisesRegex(Invalid,'storage.googleapis.com'):
            verify_routes(bad,positive,bounds)

    def test_dedicated_ai_picks_own_domains_not_shared_providers(self):
        body = ['DOMAIN-SUFFIX,chatgpt.com', 'DOMAIN,chatgpt.livekit.cloud',
                'DOMAIN-SUFFIX,livekit.cloud', 'DOMAIN-SUFFIX,claude.ai',
                'DOMAIN,ai.google.dev', 'DOMAIN,geminiweb-pa.googleapis.com',
                'DOMAIN,storage.googleapis.com', 'DOMAIN,openai.com.example.test']
        entries={e['id']:e for e in json.loads((library.ROOT/'config/catalog.json').read_text())['entries']}
        owners=[(k,read_rules((library.ROOT/'rules'/library.rule_filename(entries[k])).read_text()))
                for k in ('chatgpt-connections','gemini-connections')]
        self.assertEqual([first_policy(row.split(',')[1],owners) for row in body],
                         ['chatgpt-connections','chatgpt-connections',None,None,'gemini-connections','gemini-connections',None,None])

    def extract(self, name, doc):
        entry=next(e for e in json.loads((library.ROOT/'config/catalog.json').read_text())['entries'] if e['id']==name)
        return extract_rows(entry['extract'][0],doc)

    def test_new_apple_api_is_discovered_without_importing_shared_suffixes(self):
        raw = ('DOMAIN,se3.itunes.apple.com,{{ api_rule }}\n'
               'DOMAIN,api-v2.apps.apple.com,{{ api_rule }}\n'
               'DOMAIN,iosapps.itunes.apple.com,{{ cdn_rule }}\n'
               'DOMAIN-SUFFIX,itunes.apple.com,{{ api_rule }}\n'
               'DOMAIN,guzzoni.apple.com,{{ api_rule }}\n')
        self.assertEqual(self.extract('apple-store-transactions',raw), {'DOMAIN,se3.itunes.apple.com','DOMAIN,api-v2.apps.apple.com'})

    def test_regional_endpoints_do_not_capture_other_tenants_or_mainland(self):
        doc = ('<p>Other examples: https://foo.blob.core.windows.net '
               'https://dashscope-us.aliyuncs.com.example.test</p>'
               '<table><tr><td>Region</td><td>OpenAI-compatible</td><td>Anthropic-compatible</td></tr>'
               '<tr><td>US (Virginia)</td><td>https://dashscope-us.aliyuncs.com/api</td>'
               '<td>https://dashscope-us.aliyuncs.com/apps/anthropic</td></tr>'
               '<tr><td>China (Beijing)</td><td>https://dashscope.aliyuncs.com/api</td>'
               '<td>https://dashscope.aliyuncs.com/apps/anthropic</td></tr></table>')
        self.assertEqual(self.extract('qwen-international',doc), {'DOMAIN,dashscope-us.aliyuncs.com'})

    def test_official_sources_do_not_mix_private_relay_with_cloud_storage(self):
        def tab(id, rows):
            return f'<h2 id="{id}"></h2><table>'+''.join(
                f'<tr><td>{host}</td><td>443</td><td>TCP</td><td>iOS</td><td>{role}</td></tr>'
                for host,role in rows
            )+'</table>'
        source=tab('appleaccount',[('appleid.cdn-apple.com','Apple Account authentication')])
        source+=tab('icloud',[('*.icloud-content.com','iCloud services'),
                   ('mask.icloud.com','iCloud Private Relay'),('apple-native-relay.apple.com','RCS')])
        self.assertEqual(self.extract('apple-account-authentication',source),{'DOMAIN,appleid.cdn-apple.com'})
        self.assertEqual(self.extract('apple-icloud-content-domains',source),{'DOMAIN-SUFFIX,icloud-content.com'})

    def test_unicode_domain_can_be_kept_in_its_native_form(self):
        self.assertEqual(read_rules('DOMAIN-SUFFIX,mi.中国'), ['DOMAIN-SUFFIX,mi.中国'])

    def test_specific_apple_and_claude_precede_general_rules(self):
        data=[('AppleAuth',['DOMAIN,appleid.cdn-apple.com']), ('iCloud',['DOMAIN-SUFFIX,cdn-apple.com']),
              ('Claude',['DOMAIN-SUFFIX,anthropic.com']), ('AI-Foreign',['DOMAIN-KEYWORD,anthropic'])]
        self.assertEqual(first_policy('appleid.cdn-apple.com', data), 'AppleAuth')
        self.assertEqual(first_policy('api.anthropic.com', data), 'Claude')
        self.assertIsNone(first_policy('unrelated.cdn-apple.com.attacker.test', data))
