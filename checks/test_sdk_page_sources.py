"""Follow a page's current SDK and read only its declared production object."""
import copy
import json

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class SdkPageSources(PublicSourceExamples):
    def fixture(self, build='v1', host='login.vendor.example'):
        source = 'https://video.vendor.example/'
        sdk = 'https://cdn.sdk.example/' + build + '/sdk.js'
        spec = {'method': 'next-sdk', 'source': source, 'max-documents': 1,
                'asset-roots': ['sdk.example'],
                'config': {'identity': [{'path': ['product'], 'equals': 'Video'},
                                        {'path': ['identity', 'environment'], 'equals': 'prod'}],
                           'paths': [['identity', 'scriptUrl']]},
                'document': {'format': 'literal-object-urls', 'object-key': 'prod',
                             'fields': ['authority', 'orchestrationURL', 'telemetryURL']}}
        html = ('<script id="__NEXT_DATA__" type="application/json">' + json.dumps({
            'product': 'Video', 'identity': {'environment': 'prod', 'scriptUrl': sdk}}) + '</script>')
        script = ('const environments={qa:{authority:"https://qa.other.example"},'
                  'prod:{authority:"https://' + host + '",orchestrationURL:"https://' + host + '/v1",'
                  'telemetryURL:"https://log.vendor.example"}};')
        return spec, html, {sdk: script}

    def test_selected_production_object_ignores_comments_examples_and_other_environments(self):
        spec, _, inputs = self.fixture()
        recipe = spec['document']
        body = next(iter(inputs.values()))
        body = ('// prod:{authority:"https://comment.example"}\n'
                'const sample="prod:{authority: notAnObject}";'
                'const environmentNames={prod:"prod",qa:"qa"};'
                r'const encoded="a/b".replace(/\//g,"_");'
                'const template=`prod:{authority: notAnObject}`;' + body)
        self.assertEqual(extract_rows(recipe, body),
                         {'DOMAIN,login.vendor.example', 'DOMAIN,log.vendor.example'})
        self.assertEqual(extract_rows(recipe, body.replace('login.vendor.example', 'new.unlisted.example')),
                         {'DOMAIN,new.unlisted.example', 'DOMAIN,log.vendor.example'})
        for change in ('missing', 'extra', 'computed', 'duplicate', 'multiple'):
            altered = body
            if change == 'missing': altered = body.replace('telemetryURL:', 'otherField:')
            if change == 'extra': altered = body.replace('prod:{', 'prod:{extraURL:"https://extra.example",')
            if change == 'computed': altered = body.replace('"https://login.vendor.example"', 'computeUrl()')
            if change == 'duplicate': altered = body.replace('prod:{', 'prod:{authority:"https://duplicate.example",')
            if change == 'multiple': altered += next(iter(inputs.values()))
            with self.subTest(change=change), self.assertRaises(Invalid): extract_rows(recipe, altered)

    def test_sdk_versions_and_hosts_follow_the_page_and_forged_reports_fail(self):
        from loon_rules.sources import expansion
        for build, host in [('v1', 'login.vendor.example'), ('v2', 'new-api.unlisted.example')]:
            spec, html, inputs = self.fixture(build, host)
            rows, report, _ = expansion.collect({'account': {'expand': spec}},
                                               {spec['source']: html}, inputs.__getitem__)
            self.assertIn('DOMAIN,' + host, rows['account'])
            self.assertIn('DOMAIN,cdn.sdk.example', rows['account'])
            expansion.verify_report({'account': {'expand': spec}}, rows, report)
            for changed in ('source', 'role', 'body'):
                bad = copy.deepcopy(report)
                if changed == 'source': bad['account']['documents'][0]['source'] = 'https://other.example/sdk.js'
                if changed == 'role': bad['account']['documents'][0]['roles'].pop('authority')
                if changed == 'body': bad['account']['documents'][0]['rows'].append('DOMAIN,unrelated.example')
                with self.subTest(changed=changed), self.assertRaises(Invalid):
                    expansion.verify_report({'account': {'expand': spec}}, rows, bad)

    def test_exact_source_host_identity_does_not_claim_the_parent_domain(self):
        recipe = {'format': 'site-identity', 'source': 'https://my.vendor.example/',
                  'scope': 'source-host', 'brand-field': 'og:title', 'brand': 'Account'}
        body = '<meta property="og:title" content="Account">'
        self.assertEqual(extract_rows(recipe, body), {'DOMAIN,my.vendor.example'})
        for changed in (body.replace('Account', 'Other'), body + body,
                        body + '<link rel="canonical" href="https://wrong.example/">'):
            with self.subTest(changed=changed), self.assertRaises(Invalid): extract_rows(recipe, changed)

    def test_sdk_page_identity_url_types_and_asset_scope_fail_before_fetching(self):
        from loon_rules.sources import expansion
        spec, html, inputs = self.fixture()
        for changed in ('identity', 'environment', 'url-type', 'url-scope', 'url-query', 'incomplete'):
            document = {'product': 'Video', 'identity': {'environment': 'prod', 'scriptUrl': next(iter(inputs))}}
            if changed == 'identity': document['product'] = 'Other'
            if changed == 'environment': document['identity']['environment'] = 'qa'
            if changed == 'url-type': document['identity']['scriptUrl'] = {'url': next(iter(inputs))}
            if changed == 'url-scope': document['identity']['scriptUrl'] = 'https://other.example/sdk.js'
            if changed == 'url-query': document['identity']['scriptUrl'] += '?credential=value'
            body = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(document) + '</script>'
            if changed == 'incomplete': body = body.removesuffix('</script>')
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                expansion.collect({'account': {'expand': spec}}, {spec['source']: body}, inputs.__getitem__)

    def test_page_changes_reach_bundle_and_clients_and_broken_sdk_keeps_all_outputs(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        from loon_rules.exports import publish
        spec, html, inputs = self.fixture()
        entry = {'id': 'account', 'mode': 'compiled', 'priority': 20, 'section': 'vendors',
                 'description': '共用账户', 'boundary': 'SDK 与生产入口', 'sources': [spec['source']], 'expand': spec}
        bundle = {'id': 'accounts-all', 'mode': 'view', 'priority': 10, 'section': 'vendors',
                  'description': '合集', 'boundary': '替代账户细分', 'members': ['account']}
        config = {'schema-version': 2, 'entries': [bundle, entry], 'critical': {}, 'shared-negatives': [],
                  'sections': [{'id': 'vendors', 'title': '厂商'}]}
        urls = {spec['source']: html, **inputs}
        with TemporaryDirectory() as tmp, patch.object(lib, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp); (root / 'rules').mkdir()
            entries = lib.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(lib.render_index(config, entries))
            for product in entries.values():
                (root / 'rules' / lib.rule_filename(product)).write_text(lib.decorate(product,
                    ['DOMAIN,login.vendor.example'], None, '2026-11-20T00:00:00Z'))
            with patch.object(lib.transport, 'download', side_effect=urls.__getitem__):
                lib.run(); publish(root)
                _, new_html, new_inputs = self.fixture('v2')
                new_inputs = {key: value.replace('https://login.vendor.example/v1', 'https://new-api.unlisted.example/v1')
                              for key, value in new_inputs.items()}
                urls.update(new_inputs); urls[spec['source']] = new_html
                lib.run(); publish(root)
                for product in (entry, bundle):
                    path = root / 'rules' / lib.rule_filename(product)
                    self.assertIn('DOMAIN,new-api.unlisted.example', lib.rules.read_rules(path.read_text()))
                    self.assertEqual(path.read_bytes(), path.with_suffix('.list').read_bytes())
                    self.assertIn('new-api.unlisted.example',
                                  (root / 'dist/sing-box' / path.with_suffix('.json').name).read_text())
                self.assertEqual(lib.run(offline=True), 0)
                before = {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                          for p in (root / folder).rglob('*') if p.is_file()}
                urls.update({key: value.replace('prod:{', 'staging:{') for key, value in new_inputs.items()})
                with self.assertRaises(Invalid): lib.run()
                self.assertEqual(before, {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                                         for p in (root / folder).rglob('*') if p.is_file()})
