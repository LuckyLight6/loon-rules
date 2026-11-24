"""Provider scopes come from published fields, not a copied application dependency list."""
from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class ProviderSources(PublicSourceExamples):
    def test_named_service_table_follows_new_regions_without_claiming_shared_login(self):
        recipe = {'format': 'purpose-host-table', 'section': 'core',
                  'headers': ['URL', 'Purpose'], 'purpose-prefixes': ['Model service'],
                  'value-format': 'domain', 'all-exact': True}
        body = ('<h2 id="core">Core</h2><table><tr><td>URL</td><td>Purpose</td></tr>'
                '<tr><td>runtime.vendor.example</td><td>Model service (US)</td></tr>'
                '<tr><td>login.shared.example</td><td>Shared account sign-in</td></tr>'
                '<tr><td>telemetry.vendor.example</td><td>Optional telemetry</td></tr></table>')
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN,runtime.vendor.example'})
        changed = body.replace('</table>', '<tr><td>runtime.new-region.example</td>'
                               '<td>Model service (New region)</td></tr></table>')
        self.assertEqual(extract_rows(recipe, changed), {
            'DOMAIN,runtime.vendor.example', 'DOMAIN,runtime.new-region.example'})
        with self.assertRaises(Invalid):
            extract_rows(recipe, body, shared_hosts={'runtime.vendor.example'})
        for host in ('*.shared.example', 'not a host', 'https://user:password@shared.example'):
            with self.subTest(host=host), self.assertRaises(Invalid):
                extract_rows(recipe, body.replace('runtime.vendor.example', host))
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('Model service', 'Different product'))
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('Model service', 'Model services-unrelated'))

    def test_unlisted_endpoint_and_registry_change_reach_views_and_client_outputs(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        import json
        from checks.source_fixtures import prepare_workspace
        from loon_rules.generation import pipeline as lib
        from loon_rules.exports import publish
        endpoint='https://docs.vendor.example/allowlist'
        registry='https://rdap.example/entity/ORG-SERVICE'
        feed='https://rules.example/service.list'
        recipe={'format':'domain-column-table','source':endpoint,'section':'endpoints',
                'headers':['Domain','Purpose'],'column':'Domain','value-format':'url'}
        service={'id':'service','priority':20,'mode':'compiled','section':'development',
                 'description':'服务','boundary':'官方服务入口与自有网络','sources':[endpoint,registry,feed],
                 'projection':[{'source':feed,'roots':['vendor.example'],
                                'require-domain-closure':True}],
                 'ip-match':'target-ip','extract':[recipe,{
                     'format':'rdap-entity-autnums','source':registry,
                     'registrant-id':'ORG-SERVICE','registrant-name':'Service Operator'}]}
        combined={'id':'services-all','priority':10,'mode':'view','section':'development',
                  'description':'合集','boundary':'替代服务细分','members':['service']}
        config={'schema-version':2,'entries':[combined,service],
                'sections':[{'id':'development','title':'开发'}],
                'critical':{'api.vendor.example':['service']},'shared-negatives':[],
                'source-inventories':[{'id':'complete-allowlist','source':endpoint,
                                       'recipe':recipe,'owners':['service']}]}
        def document(extra=''):
            return ('<h2 id="endpoints">Endpoints</h2><table><tr><td>Domain</td><td>Purpose</td></tr>'
                    '<tr><td>https://api.vendor.example</td><td>API</td></tr>'+extra+'</table>')
        record={'objectClassName':'entity','handle':'ORG-SERVICE',
                'vcardArray':['vcard',[['fn',{},'text','Service Operator']]],
                'autnums':[{'objectClassName':'autnum','handle':'AS399358',
                            'startAutnum':399358,'endAutnum':399358,'status':['active']}]}
        inputs={endpoint:document(),registry:json.dumps(record),feed:'DOMAIN,api.vendor.example'}
        with TemporaryDirectory() as tmp, patch.object(lib,'ROOT',prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(config)
            (root/'config/catalog.json').write_text(json.dumps(config))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(config,entries))
            for entry in entries.values():
                (root/'rules'/lib.rule_filename(entry)).write_text(lib.decorate(entry,
                    ['DOMAIN,api.vendor.example','IP-ASN,399358,no-resolve'],None,'2026-11-20T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=inputs.__getitem__):
                lib.run();publish(root)
                inputs[endpoint]=document('<tr><td>https://files.unlisted-provider.example</td><td>New product</td></tr>')
                inputs[feed]+='\nDOMAIN,files.unlisted-provider.example'
                record['autnums']=[{'objectClassName':'autnum','handle':'AS399359',
                                   'startAutnum':399359,'endAutnum':399359,'status':['active']}]
                inputs[registry]=json.dumps(record)
                lib.run();publish(root);lib.run();publish(root,check=True)
                for entry in (service,combined):
                    path=root/'rules'/lib.rule_filename(entry)
                    rows=lib.rules.read_rules(path.read_text())
                    self.assertIn('DOMAIN,files.unlisted-provider.example',rows)
                    self.assertIn('IP-ASN,399359,no-resolve',rows)
                    self.assertNotIn('IP-ASN,399358,no-resolve',rows)
                    self.assertEqual(path.read_bytes(),path.with_suffix('.list').read_bytes())
                    yaml=(root/'dist/clash-classical'/path.with_suffix('.yaml').name).read_text()
                    self.assertIn('files.unlisted-provider.example',yaml)
                    self.assertIn('IP-ASN,399359,no-resolve',yaml)
                before={p:p.read_bytes() for folder in ('rules','dist')
                        for p in (root/folder).rglob('*') if p.is_file()}
                state=(root/'data/maintenance-state.json').read_bytes()
                inputs[feed]+='\nDOMAIN,new.unassigned.example'
                with self.assertRaisesRegex(Invalid,'未处理|完整'):
                    lib.run()
                self.assertTrue(all(p.read_bytes()==body for p,body in before.items()))
                self.assertEqual((root/'data/maintenance-state.json').read_bytes(),state)
                inputs[feed]=inputs[feed].removesuffix('\nDOMAIN,new.unassigned.example')
                record['vcardArray'][1][0][3]='Other Operator';inputs[registry]=json.dumps(record)
                with self.assertRaises(Invalid):lib.run()
                self.assertTrue(all(p.read_bytes()==body for p,body in before.items()))

    def test_registry_organization_discovers_new_asns_without_a_fixed_number_list(self):
        import json
        recipe = {'format': 'rdap-entity-autnums', 'registrant-id': 'ORG-SERVICE',
                  'registrant-name': 'Service Operator'}
        def autnum(number):
            return {'objectClassName': 'autnum', 'handle': 'AS'+str(number),
                    'startAutnum': number, 'endAutnum': number, 'status': ['active']}
        record = {'objectClassName': 'entity', 'handle': 'ORG-SERVICE',
                  'vcardArray': ['vcard', [['fn', {}, 'text', 'Service Operator'],
                                          ['kind', {}, 'text', 'org']]],
                  'autnums': [autnum(399358)]}
        self.assertEqual(extract_rows(recipe, json.dumps(record)), {'IP-ASN,399358,no-resolve'})
        record['autnums'].append(autnum(399359))
        self.assertEqual(extract_rows(recipe, json.dumps(record)), {
            'IP-ASN,399358,no-resolve', 'IP-ASN,399359,no-resolve'})
        import copy
        for change in ('owner', 'identity', 'range', 'private', 'truncated', 'empty'):
            bad = copy.deepcopy(record)
            if change == 'owner': bad['vcardArray'][1][0][3] = 'Other Operator'
            elif change == 'identity': bad['handle'] = 'ORG-OTHER'
            elif change == 'range': bad['autnums'][1]['endAutnum'] += 1
            elif change == 'private': bad['autnums'].append(autnum(64512))
            elif change == 'truncated':
                bad['notices'] = [{'title': 'Response truncated due to authorization'}]
            else: bad['autnums'] = []
            with self.subTest(change=change), self.assertRaises(Invalid):
                extract_rows(recipe, json.dumps(bad))

    def test_url_column_follows_new_hosts_and_purposes_without_root_filters(self):
        recipe = {'format': 'domain-column-table', 'section': 'endpoints',
                  'headers': ['Domain', 'Purpose'], 'column': 'Domain', 'value-format': 'url'}
        def document(url='https://api.vendor.example', purpose='API'):
            return ('<h2 id="endpoints">Endpoints</h2><table>'
                    '<tr><td>Domain</td><td>Purpose</td></tr>'
                    '<tr><td>'+url+'</td><td>'+purpose+'</td></tr></table>')
        self.assertEqual(extract_rows(recipe, document()), {'DOMAIN,api.vendor.example'})
        self.assertEqual(extract_rows(recipe, document('https://brand-new.example/v1','New product')),
                         {'DOMAIN,brand-new.example'})
        for value in ('https://127.0.0.1', 'https://example:example@api.vendor.example',
                      'http://api.vendor.example', 'https://api.vendor.example?secret=value'):
            with self.subTest(url=value), self.assertRaises(Invalid):
                extract_rows(recipe, document(value))

    def test_existing_api_field_reader_can_follow_a_raw_sdk_constant_without_a_host_filter(self):
        recipe = {'format': 'code-api-endpoints', 'markup': 'source', 'api-fields': ['ENDPOINT']}
        body = ('// ENDPOINT = "https://comment.example";\n'
                'const other = "ENDPOINT = \'https://inside-string.example\'";\n'
                'export const ENDPOINT = "https://registration.vendor.example/v1";')
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN,registration.vendor.example'})
        changed = body.replace('registration.vendor.example', 'new-api.other-provider.example')
        self.assertEqual(extract_rows(recipe, changed), {'DOMAIN,new-api.other-provider.example'})
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('"https://registration.vendor.example/v1"', 'configuredAtRuntime'))

    def test_owned_https_namespace_ignores_unrelated_malformed_url_examples(self):
        recipe = {'format': 'https-hosts', 'workspace-roots': ['vendor.example']}
        body = ('<p>Use https://inquiry.vendor.example/ for this service.</p>'
                '<script>const template = "https://[region].other.example";</script>')
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN-SUFFIX,vendor.example'})

    def test_domain_column_follows_new_regions_without_copying_the_other_columns(self):
        recipe = {'format': 'domain-column-table', 'section': 'sites',
                  'headers': ['Region', 'Portal', 'Site', 'Location'], 'column': 'Site',
                  'domain-scope': 'domain-and-subdomains'}
        def row(*cells):
            return '<tr>' + ''.join('<td>' + cell + '</td>' for cell in cells) + '</tr>'
        body = '<h2 id="sites">Sites</h2><table>' + row(*recipe['headers'])
        body += row('US', 'https://app.platform.example', 'platform.example', 'US')
        body += row('NEW', 'https://portal.new-provider.example', 'new-provider.example', 'New')
        body += '</table><h2 id="other">Other</h2><table>' + row('wrong.example') + '</table>'
        self.assertEqual(extract_rows(recipe, body), {
            'DOMAIN-SUFFIX,platform.example', 'DOMAIN-SUFFIX,new-provider.example'})
        for bad in (body.replace('id="sites"', 'id="elsewhere"'),
                    body.replace('<td>Site</td>', '<td>Changed column</td>'),
                    body.replace('<td>new-provider.example</td>', '<td>127.0.0.1</td>')):
            with self.subTest(body=bad), self.assertRaises(Invalid):
                extract_rows(recipe, bad)

    def test_csp_reads_owned_origins_and_keeps_other_embedded_products_separate(self):
        recipe = {'format': 'csp-origins', 'directives': ['connect-src', 'img-src'],
                  'brand-prefixes': ['support'], 'domain-scope': 'domain-and-subdomains'}
        body = ('<pre><code>connect-src:\n https://api.support.example\n'
                ' wss://*.support-messenger.example;\n'
                'img-src: blob: data: https://*.support-attachments.example\n'
                ' https://player.other-vendor.example;\n'
                'style-src: \'unsafe-inline\';</code></pre>')
        self.assertEqual(extract_rows(recipe, body), {
            'DOMAIN-SUFFIX,api.support.example', 'DOMAIN-SUFFIX,support-messenger.example',
            'DOMAIN-SUFFIX,support-attachments.example'})
        changed = body.replace('https://api.support.example',
                               'https://api.support.example https://cdn.support-new-region.example')
        self.assertIn('DOMAIN-SUFFIX,cdn.support-new-region.example', extract_rows(recipe, changed))
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('wss://*.support-messenger.example',
                                              'wss://user:password@support-messenger.example'))

    def test_csp_section_can_read_inline_table_fields_and_ignores_other_sections(self):
        recipe = {'format': 'csp-origins', 'sections': ['intakes'],
                  'directives': ['connect-src']}
        body = ('<h4 id="intakes">Intakes</h4><p>Use <code>connect-src</code>.</p>'
                '<table><tr><td>New region</td><td><code>connect-src '
                'https://intake.new-provider.example</code></td></tr></table>'
                '<h4 id="other">Other use</h4><code>connect-src https://wrong.example</code>')
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN,intake.new-provider.example'})
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('id="intakes"', 'id="changed"'))

    def test_c_function_accepts_only_a_single_literal_endpoint_and_tracks_its_changes(self):
        recipe = {'format': 'c-function-url', 'function': 'RegistrationServer'}
        body = ('// RegistrationServer(void) { return @"https://comment.example"; }\n'
                'NSString *RegistrationServer(void) {\n'
                '  return @"https://token.vendor.example/register";\n}\n'
                'NSString *OtherServer(void) { return @"https://other.example"; }')
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN,token.vendor.example'})
        self.assertEqual(extract_rows(recipe, body.replace('token.vendor.example', 'new.vendor.example')),
                         {'DOMAIN,new.vendor.example'})
        for bad in (body + body, body.replace('return @', 'if (condition) return @'),
                    body.replace('https://token.vendor.example', 'http://token.vendor.example'),
                    body.replace('https://token.vendor.example', 'https://127.0.0.1')):
            with self.subTest(body=bad), self.assertRaises(Invalid):
                extract_rows(recipe, bad)

    def test_a_provider_cannot_claim_a_shared_resolver_listed_in_its_document(self):
        recipe = {'format': 'csp-origins', 'directives': ['connect-src']}
        body = ('<pre><code>connect-src https://api.vendor.example '
                'https://resolver.shared.example;</code></pre>')
        self.assertEqual(extract_rows(recipe, body, shared_hosts=['resolver.shared.example']),
                         {'DOMAIN,api.vendor.example'})
