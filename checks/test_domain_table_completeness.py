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
