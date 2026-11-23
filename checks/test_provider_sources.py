"""Provider scopes come from published fields, not a copied application dependency list."""
from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class ProviderSources(PublicSourceExamples):
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
