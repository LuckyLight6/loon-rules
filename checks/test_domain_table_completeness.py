"""Compare every declared endpoint column with the independently generated list."""
from contextlib import redirect_stdout
from io import StringIO
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.exports import publish
from loon_rules.generation import pipeline
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class CompleteDomainTables(PublicSourceExamples):
    def recipe(self):
        return {'format': 'domain-column-table', 'section': 'telemetry',
                'headers': ['Capability', 'US', 'EU'], 'columns': ['US', 'EU'],
                'split-values': True, 'group-rows': ['Mobile']}

    def page(self, table_extra='', list_extra=''):
        return ('<h2 id="telemetry">Telemetry</h2><table>'
                '<tr><th>Capability</th><th>US</th><th>EU</th></tr>'
                '<tr><td colspan="3">Mobile</td></tr>'
                '<tr><td>Collector</td><td><code>api.vendor.example</code></td>'
                '<td><code>eu.vendor.example</code><br><code>eu2.vendor.example</code></td></tr>'
                + table_extra + '</table><h3 id="endpoint-list">Endpoint list</h3>'
                '<code>api.vendor.example</code><code>eu.vendor.example</code>'
                '<code>eu2.vendor.example</code>' + list_extra)

    def test_all_selected_columns_and_multivalue_cells_are_read_without_host_filters(self):
        try:
            rows = extract_rows(self.recipe(), self.page())
        except (Invalid, KeyError) as error:
            self.fail('完整端点表的分组行和多列声明尚未被支持：' + str(error))
        self.assertEqual(rows, {'DOMAIN,api.vendor.example', 'DOMAIN,eu.vendor.example',
                                'DOMAIN,eu2.vendor.example'})
        changed = self.page('<tr><td>New collector</td><td>runtime.unprefilled.example</td>'
                            '<td>eu.unlisted-provider.example</td></tr>')
        self.assertEqual(extract_rows(self.recipe(), changed), rows | {
            'DOMAIN,runtime.unprefilled.example', 'DOMAIN,eu.unlisted-provider.example'})

    def test_unhandled_shared_hosting_value_cannot_be_silently_removed(self):
        recipe = {'format': 'domain-column-table', 'section': 'endpoints',
                  'headers': ['Domain'], 'column': 'Domain'}
        body = ('<h2 id="endpoints">Endpoints</h2><table><tr><td>Domain</td></tr>'
                '<tr><td>api.vendor.example</td></tr><tr><td>*.tenant.github.io</td></tr></table>')
        with self.assertRaises(Invalid):
            extract_rows(recipe, body)
        with self.assertRaises(Invalid):
            extract_rows(recipe, body.replace('*.tenant.github.io', 'resolver.shared.example'),
                         shared_hosts=['resolver.shared.example'])

    def test_changed_columns_group_roles_and_bad_values_stop_the_whole_table(self):
        for body in (self.page().replace('colspan="3">Mobile', 'colspan="3">Unknown scope'),
                     self.page().replace('<th>EU</th>', '<th>APAC</th>'),
                     self.page().replace('<td>Collector</td>', ''),
                     self.page().replace('eu2.vendor.example', '127.0.0.1'),
                     self.page().replace('eu2.vendor.example', '*.tenant.github.io')):
            with self.subTest(body=body), self.assertRaises(Invalid):
                extract_rows(self.recipe(), body)

    def test_column_options_are_unambiguous_and_urls_are_not_split_like_domains(self):
        for change in ({'columns': []}, {'columns': ['US', 'US']}, {'column': 'US'},
                       {'split-values': 1}, {'group-rows': ['Mobile', 'Mobile']},
                       {'value-format': 'url'}):
            with self.subTest(change=change), self.assertRaises(Invalid):
                extract_rows({**self.recipe(), **change}, self.page())

    def test_full_table_blocks_a_new_endpoint_missing_from_the_published_simple_list(self):
        source = 'https://docs.vendor.example/network'
        service = {'id': 'telemetry', 'mode': 'compiled', 'priority': 20, 'section': 'development',
                   'description': '遥测', 'boundary': '官方全部地区入口', 'sources': [source],
                   'extract': [{'source': source, 'format': 'section-code-domains',
                                'sections': ['endpoint-list']}]}
        combined = {'id': 'telemetry-all', 'mode': 'view', 'priority': 10, 'section': 'development',
                    'description': '合集', 'boundary': '替代细分', 'members': ['telemetry']}
        config = {'schema-version': 2, 'entries': [combined, service],
                  'sections': [{'id': 'development', 'title': '开发'}],
                  'critical': {'api.vendor.example': ['telemetry']}, 'shared-negatives': [],
                  'source-inventories': [{'id': 'complete-table', 'source': source,
                                          'recipe': self.recipe(), 'owners': ['telemetry']}]}
        inputs = {source: self.page()}
        with TemporaryDirectory() as temporary, patch.object(pipeline, 'ROOT', prepare_workspace(temporary)), redirect_stdout(StringIO()):
            root = prepare_workspace(temporary)
            (root / 'rules/loon').mkdir(parents=True)
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for entry in entries.values():
                (root / 'rules/loon' / pipeline.rule_filename(entry)).write_text(pipeline.decorate(
                    entry, ['DOMAIN,api.vendor.example', 'DOMAIN,eu.vendor.example', 'DOMAIN,eu2.vendor.example'],
                    None, '2026-11-26T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                publish(root)
                before = {path: path.read_bytes() for folder in ('rules', 'data')
                          for path in (root / folder).rglob('*') if path.is_file()}
                extra = ('<tr><td>New region</td><td>runtime.unprefilled.example</td>'
                         '<td>eu.vendor.example</td></tr>')
                inputs[source] = self.page(extra)
                with self.assertRaises(Invalid):
                    pipeline.run()
                self.assertEqual(before, {path: path.read_bytes() for folder in ('rules', 'data')
                                         for path in (root / folder).rglob('*') if path.is_file()})
                inputs[source] = self.page(extra, '<code>runtime.unprefilled.example</code>')
                pipeline.run()
                publish(root)
                for key in ('telemetry', 'telemetry-all'):
                    path = root / 'rules/loon' / pipeline.rule_filename(entries[key])
                    self.assertIn('DOMAIN,runtime.unprefilled.example', pipeline.rules.read_rules(path.read_text()))
                    self.assertIn('runtime.unprefilled.example', (root / 'rules/sing-box' / path.with_suffix('.json').name).read_text())

    def test_declared_escaped_wildcards_and_single_tenant_assets_keep_their_scope(self):
        recipe={'format':'domain-column-table','section':'ui','headers':['Domain','Purpose'],'column':'Domain',
                'decode-escaped-wildcards':True,'allow-tenant-wildcards':True}
        page=r'<h2 id="ui">UI</h2><table><tr><th>Domain</th><th>Purpose</th></tr><tr><td>\*.vendor.example</td><td>UI</td></tr><tr><td>*.assets.github.io</td><td>Assets</td></tr></table>'
        self.assertEqual(extract_rows(recipe,page),{'DOMAIN-WILDCARD,*.vendor.example','DOMAIN-WILDCARD,*.assets.github.io'})
        for changed in [page.replace('*.assets.github.io','*.github.io'),page.replace(r'\*.vendor.example',r'\vendor.example')]:
            with self.assertRaises(Invalid):extract_rows(recipe,changed)
        for field in ['decode-escaped-wildcards','allow-tenant-wildcards']:
            with self.assertRaises(Invalid):extract_rows({**recipe,field:'true'},page)

    def test_row_selection_still_validates_every_cell_before_filtering(self):
        recipe={'format':'domain-column-table','section':'ui','headers':['Domain','Purpose'],'column':'Domain',
                'select':{'roots':['vendor.example']}}
        body='<h2 id="ui">UI</h2><table><tr><th>Domain</th><th>Purpose</th></tr><tr><td>api.vendor.example</td><td>API</td></tr><tr><td>fonts.shared.example</td><td>Font</td></tr></table>'
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,api.vendor.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,body.replace('fonts.shared.example','127.0.0.1'))

    def test_endpoint_columns_accept_declared_domain_or_url_values_and_pipe_separators(self):
        recipe={'format':'domain-column-table','section':'api','headers':['Endpoint','Purpose'],'column':'Endpoint',
                'value-format':'domain-or-url','split-values':True}
        body='<h2 id="api">API</h2><table><tr><th>Endpoint</th><th>Purpose</th></tr><tr><td>api.vendor.example/ | https://api.eu.vendor.example/v1</td><td>API</td></tr></table>'
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,api.vendor.example','DOMAIN,api.eu.vendor.example'})
        for changed in [body.replace('https://api.eu.vendor.example/v1','https://user@api.eu.vendor.example/'),
                        body.replace('api.vendor.example/','api.vendor.example/other')]:
            with self.assertRaises(Invalid):extract_rows(recipe,changed)

    def test_explicit_table_identity_handles_known_companions_and_rejects_new_tables(self):
        recipe={'format':'domain-column-table','section':'agents','headers':['Endpoint','Purpose'],'column':'Endpoint',
                'other-table-headers':[['Language','Code']]}
        first='<table><tr><th>Endpoint</th><th>Purpose</th></tr><tr><td>api.vendor.example</td><td>Ingest</td></tr></table>'
        other='<table><tr><th>Language</th><th>Code</th></tr><tr><td>Python</td><td>configure_client()</td></tr></table>'
        body='<h2 id="agents">Agents</h2>'+first+other
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,api.vendor.example'})
        for changed in [body+first,body.replace('<th>Code</th>','<th>Unknown purpose</th>'),
                        body.replace('<td>Ingest</td>',''),body+other,
                        body.replace(other,''),
                        body.replace('<td>configure_client()</td>',''),
                        body.replace('<td>configure_client()</td>','<td>configure_client()</td><td>new.unlisted.example</td>')]:
            with self.subTest(changed=changed),self.assertRaises(Invalid):extract_rows(recipe,changed)

    def test_bare_endpoint_references_and_copy_controls_are_explicit(self):
        recipe={'format':'domain-column-table','section':'agents','headers':['Endpoint'],'column':'Endpoint',
                'value-format':'domain-or-url','allow-bare-addresses':True,'ignore-controls':True,'split-values':True}
        body='<h2 id="agents">Agents</h2><table><tr><th>Endpoint</th></tr><tr><td>api.vendor.example:4317/path/</td></tr><tr><td>https://eu.vendor.example< button>Copy</button></td></tr></table>'.replace('< button>','<button>')
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,api.vendor.example','DOMAIN,eu.vendor.example'})
        for changed in [body.replace('api.vendor.example:4317/path/','user@api.vendor.example:443/'),
                        body.replace('api.vendor.example:4317/path/','api.vendor.example:abc/')]:
            with self.assertRaises(Invalid):extract_rows(recipe,changed)

    def test_dedicated_assets_follow_their_documented_purpose_without_pinning_hosts(self):
        recipe={'format':'domain-column-table','section':'assets','headers':['Host','Purpose'],'column':'Host',
                'select':{'purpose-column':'Purpose','purpose-prefixes':['Dedicated product assets']}}
        body='<h2 id="assets">Assets</h2><table><tr><th>Host</th><th>Purpose</th></tr><tr><td>new-tenant.s3.amazonaws.com</td><td>Dedicated product assets in a new region</td></tr><tr><td>fonts.shared.example</td><td>Shared fonts</td></tr></table>'
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,new-tenant.s3.amazonaws.com'})
        with self.assertRaises(Invalid):extract_rows(recipe,body.replace('fonts.shared.example','127.0.0.1'))

    def test_explicit_repeated_tables_consume_each_complete_table_in_the_section(self):
        recipe = {'format': 'domain-column-table', 'section': 'core', 'headers': ['URL', 'Purpose'],
                  'column': 'URL', 'allow-repeated-tables': True}
        first = '<table><tr><th>URL</th><th>Purpose</th></tr><tr><td>app.product.example</td><td>Login</td></tr></table>'
        second = '<table><tr><th>URL</th><th>Purpose</th></tr><tr><td>api.product.example</td><td>Service</td></tr></table>'
        body = '<h2 id="core">Core</h2>' + first + second
        try:
            result = extract_rows(recipe, body)
        except Invalid as error:
            self.fail('显式多表声明尚未完整读取：' + str(error))
        self.assertEqual(result, {'DOMAIN,app.product.example', 'DOMAIN,api.product.example'})
        for changed in (body.replace('api.product.example', '127.0.0.1'),
                        body.replace('<td>Service</td>', ''),
                        body + second.replace('<th>Purpose</th>', '<th>Unclassified</th>'),
                        body + '<table><tr><th>URL</th><th>Purpose</th></tr></table>'):
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows(recipe, changed)
