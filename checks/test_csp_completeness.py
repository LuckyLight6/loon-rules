"""An incomplete CSP source must leave the last accepted files intact."""
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


class CompleteCSPUpdates(PublicSourceExamples):
    def test_selected_csp_directive_cannot_silently_drop_shared_hosting_patterns(self):
        for scope in ('listed', 'domain-and-subdomains'):
            for prefixes in ([], ['vendor']):
                recipe = {'format': 'csp-origins', 'directives': ['connect-src'],
                          'domain-scope': scope, 'brand-prefixes': prefixes}
                for host in ('*.github.io', '*.tenant.github.io'):
                    body = ('<pre><code>connect-src https://api.vendor.example '
                            'https://' + host + ';</code></pre>')
                    with self.subTest(scope=scope, prefixes=prefixes, host=host), self.assertRaises(Invalid):
                        extract_rows(recipe, body)

    def test_changed_csp_endpoints_reach_outputs_and_incomplete_updates_write_nothing(self):
        source = 'https://docs.vendor.example/network'
        recipe = {'format': 'csp-origins', 'sections': ['service-endpoints'],
                  'directives': ['connect-src']}
        service = {'id': 'service', 'mode': 'compiled', 'priority': 20, 'section': 'development',
                   'description': '服务', 'boundary': '官方用途章节的服务入口',
                   'sources': [source], 'extract': [{'source': source, **recipe}]}
        combined = {'id': 'services-all', 'mode': 'view', 'priority': 10, 'section': 'development',
                    'description': '服务合集', 'boundary': '替代细分', 'members': ['service']}
        config = {'schema-version': 2, 'entries': [combined, service],
                  'sections': [{'id': 'development', 'title': '开发'}],
                  'critical': {'api.vendor.example': ['service']},
                  'shared-negatives': ['resolver.shared.example'],
                  'source-inventories': [{'id': 'complete-csp-endpoints', 'source': source,
                                          'recipe': recipe, 'owners': ['service']}]}

        def document(extra=''):
            return ('<h2 id="service-endpoints">Service endpoints</h2><pre><code>'
                    'connect-src https://api.vendor.example ' + extra + ';</code></pre>')

        inputs = {source: document()}
        with TemporaryDirectory() as tmp, patch.object(pipeline, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules').mkdir()
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for entry in entries.values():
                (root / 'rules' / pipeline.rule_filename(entry)).write_text(pipeline.decorate(
                    entry, ['DOMAIN,api.vendor.example'], None, '2026-11-20T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                inputs[source] = document('https://files.unlisted-provider.example')
                pipeline.run()
                publish(root)
                for entry in entries.values():
                    path = root / 'rules' / pipeline.rule_filename(entry)
                    self.assertIn('DOMAIN,files.unlisted-provider.example', pipeline.rules.read_rules(path.read_text()))
                    self.assertEqual(path.read_bytes(), path.with_suffix('.list').read_bytes())
                    output = root / 'dist/sing-box' / path.with_suffix('.json').name
                    self.assertIn('files.unlisted-provider.example', output.read_text())
                before = {path: path.read_bytes() for folder in ('rules', 'dist', 'data')
                          for path in (root / folder).rglob('*') if path.is_file()}
                for host in ('*.tenant.github.io', 'resolver.shared.example'):
                    inputs[source] = document('https://files.unlisted-provider.example https://' + host)
                    with self.subTest(host=host), self.assertRaises(Invalid):
                        pipeline.run()
                    self.assertTrue(all(path.read_bytes() == body for path, body in before.items()))
