import unittest

from maintain import Invalid, read_rules, update_feed, app_store_rules, regional_endpoints, first_policy, apple_endpoints, ai_partition, verify_routes


class RuleContracts(unittest.TestCase):
    def test_invalid_body_or_arbitrary_policy_is_not_a_rules_release(self):
        for body in ('<html>blocked</html>', '[Plugin]\nhttps://example.test/', 'DOMAIN,example.test,DIRECT',
                     'IP-CIDR,17.0.0.0/96', 'DOMAIN-SUFFIX,example.test\nFINAL,DIRECT'):
            with self.subTest(body=body), self.assertRaises(Invalid):
                read_rules(body, {'DOMAIN', 'DOMAIN-SUFFIX', 'IP-CIDR'})

    def test_verified_scope_updates_and_stale_input_leaves_cached_data(self):
        before = ['DOMAIN,api.example.test', 'DOMAIN,a.example.test']
        entry = {'id':'test','kinds':['DOMAIN'],'flags':[]}
        self.assertEqual(update_feed(entry,before,'DOMAIN,api.example.test\nDOMAIN,a.example.test\nDOMAIN,b.example.test')[-1],
                         'DOMAIN,b.example.test')
        with self.assertRaises(Invalid):
            update_feed(entry,before,'DOMAIN,b.example.test')
        with self.assertRaises(Invalid):
            update_feed(entry,before,'DOMAIN,api.example.test\nDOMAIN,a.example.test\nDOMAIN-SUFFIX,googleapis.com')

    def test_new_overbroad_entries_cannot_take_over_the_configuration(self):
        old = ['DOMAIN,api.example.test']
        entry = {'id':'test', 'kinds':['DOMAIN','DOMAIN-SUFFIX','IP-CIDR','IP-CIDR6'], 'flags':[]}
        for line in ('DOMAIN-SUFFIX,com', 'DOMAIN-SUFFIX,apple.com',
                     'IP-CIDR,16.0.0.0/7', 'IP-CIDR6,2600::/12'):
            with self.subTest(line=line), self.assertRaises(Invalid):
                update_feed(entry,old,'\n'.join(old + [line]))

    def test_no_resolve_is_for_reviewed_prefixes_only_and_survives_an_update(self):
        doc4 = 'IP-CIDR,192.0.2.0/24'
        doc6 = 'IP-CIDR6,2001:db8::/32'
        fallback = ['IP-CIDR,192.168.0.0/16', 'IP-CIDR6,64:ff9b::/96']
        entry = {'id':'reserved', 'kinds':['IP-CIDR','IP-CIDR6'], 'flags':[],
                 'literal_ips':[doc4,doc6], 'dns_required':fallback}
        expected = [doc4+',no-resolve',doc6+',no-resolve',*fallback]
        raw = '\n'.join([doc4,doc6,*fallback])
        self.assertEqual(update_feed(entry,expected,raw),expected)
        self.assertEqual(update_feed(entry,expected,raw+'\nIP-CIDR,198.18.0.0/15'),
                         expected+['IP-CIDR,198.18.0.0/15'])

    def test_does_not_drop_a_required_ip_or_turn_a_dns_fallback_into_ip_only(self):
        doc = 'IP-CIDR,192.0.2.0/24'
        fallback = 'IP-CIDR6,64:ff9b::/96'
        entry = {'id':'reserved', 'kinds':['DOMAIN','IP-CIDR','IP-CIDR6'], 'flags':['no-resolve'],
                 'literal_ips':[doc], 'dns_required':[fallback]}
        other = ['DOMAIN,example.test', 'IP-CIDR,198.51.100.0/24']
        old = [doc+',no-resolve',fallback,*other]
        for raw in ([fallback,*other], [doc,fallback+',no-resolve',*other]):
            with self.subTest(raw=raw), self.assertRaisesRegex(Invalid,'IP 匹配'):
                update_feed(entry,old,'\n'.join(raw))

    def test_an_upstream_option_change_on_a_known_ip_needs_review(self):
        entry = {'id':'test', 'kinds':['IP-ASN','DOMAIN'], 'flags':['no-resolve']}
        unchanged = [f'DOMAIN,h{i}.example.test' for i in range(10)]
        bare = 'IP-ASN,64496'
        for old, updated in ((bare, bare+',no-resolve'), (bare+',no-resolve', bare)):
            with self.subTest(updated=updated), self.assertRaisesRegex(Invalid,'IP 匹配'):
                update_feed(entry,unchanged+[old],'\n'.join(unchanged+[updated]))

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
        self.assertEqual(ai_partition(body,'OpenAI'),body[:2])
        self.assertEqual(ai_partition(body,'Gemini'),body[4:6])
        self.assertEqual(ai_partition(body,'AI-Foreign'),[body[i] for i in (2,3,6,7)])

    def test_new_apple_api_is_discovered_without_importing_shared_suffixes(self):
        raw = ('DOMAIN,se3.itunes.apple.com,{{ api_rule }}\n'
               'DOMAIN,api-v2.apps.apple.com,{{ api_rule }}\n'
               'DOMAIN,iosapps.itunes.apple.com,{{ cdn_rule }}\n'
               'DOMAIN-SUFFIX,itunes.apple.com,{{ api_rule }}\n'
               'DOMAIN,guzzoni.apple.com,{{ api_rule }}\n')
        self.assertEqual(app_store_rules(raw), {'DOMAIN,se3.itunes.apple.com','DOMAIN,api-v2.apps.apple.com'})

    def test_regional_endpoints_do_not_capture_other_tenants_or_mainland(self):
        doc = ('US endpoint: https://dashscope-us.aliyuncs.com/api; '
               'China https://dashscope.aliyuncs.com; '
               'example https://foo.blob.core.windows.net '
               'https://dashscope-us.aliyuncs.com.example.test')
        self.assertEqual(regional_endpoints(doc), {'DOMAIN,dashscope-us.aliyuncs.com'})

    def test_official_sources_do_not_mix_private_relay_with_cloud_storage(self):
        def tab(id, rows):
            return f'<h2 id="{id}"></h2><table>'+''.join(
                f'<tr><td>{host}</td><td>443</td><td>TCP</td><td>iOS</td><td>{role}</td></tr>'
                for host,role in rows
            )+'</table>'
        source=tab('appleaccount',[('appleid.cdn-apple.com','Apple Account authentication')])
        source+=tab('icloud',[('*.icloud-content.com','iCloud services'),
                   ('mask.icloud.com','iCloud Private Relay'),('apple-native-relay.apple.com','RCS')])
        self.assertEqual(apple_endpoints(source,'apple-auth'),{'DOMAIN,appleid.cdn-apple.com'})
        self.assertEqual(apple_endpoints(source,'icloud'),{'DOMAIN-SUFFIX,icloud-content.com'})

    def test_unicode_domain_can_be_kept_in_its_native_form(self):
        self.assertEqual(read_rules('DOMAIN-SUFFIX,mi.中国'), ['DOMAIN-SUFFIX,mi.中国'])

    def test_specific_apple_and_claude_precede_general_rules(self):
        data=[('AppleAuth',['DOMAIN,appleid.cdn-apple.com']), ('iCloud',['DOMAIN-SUFFIX,cdn-apple.com']),
              ('Claude',['DOMAIN-SUFFIX,anthropic.com']), ('AI-Foreign',['DOMAIN-KEYWORD,anthropic'])]
        self.assertEqual(first_policy('appleid.cdn-apple.com', data), 'AppleAuth')
        self.assertEqual(first_policy('api.anthropic.com', data), 'Claude')
        self.assertIsNone(first_policy('unrelated.cdn-apple.com.attacker.test', data))
