"""Product identities and purpose fields in public, embedded page data."""
import copy
import json

from checks.source_fixtures import PublicSourceExamples, prepare_workspace
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class EmbeddedServiceSources(PublicSourceExamples):
    def recipe(self):
        return {
            'format': 'next-service-urls',
            'source': 'https://video.vendor.example/',
            'identity': [
                {'path': ['page'], 'equals': '/[[...path]]'},
                {'path': ['config', 'application'], 'equals': 'Video'},
                {'path': ['config', 'environment'], 'equals': 'prod'},
            ],
            'paths': [['config', 'orchestrationUrl'], ['config', 'content', 'default']],
            'url-fields': [{'path': ['document'], 'fields': ['imageUrl']}],
        }

    def document(self):
        return {
            'page': '/[[...path]]',
            'config': {
                'application': 'Video', 'environment': 'prod',
                'orchestrationUrl': 'https://api.vendor.example/graph/v1',
                'content': {'default': 'https://content.vendor.example',
                            'internal': 'https://backend.internal.example'},
                'previewUrl': 'https://preview.other.example',
            },
            'document': {'children': [
                {'type': 'paragraph', 'link': 'https://unrelated.other.example'},
                {'metadata': {'rating': {'imageUrl': 'https://images.vendor.example/rating.png'}}},
            ]},
            'diagnostics': {'imageUrl': 'https://diagnostics.other.example/screenshot.png'},
        }

    def html(self, document=None):
        return ('<script src="https://tracker.other.example/run.js"></script>'
                '<script id="__NEXT_DATA__" type="application/json">'
                + json.dumps(self.document() if document is None else document)
                + '</script>')

    def test_read_product_api_and_image_fields_without_internal_preview_or_tracking_links(self):
        self.assertEqual(extract_rows(self.recipe(), self.html()), {
            'DOMAIN,api.vendor.example', 'DOMAIN,content.vendor.example',
            'DOMAIN,images.vendor.example',
        })
        document = self.document()
        document['config']['orchestrationUrl'] = 'https://new-api.unlisted-provider.example/graph'
        document['document']['children'].append({'imageUrl': 'https://new-images.unlisted.example/a.png'})
        rows = extract_rows(self.recipe(), self.html(document))
        self.assertIn('DOMAIN,new-api.unlisted-provider.example', rows)
        self.assertIn('DOMAIN,new-images.unlisted.example', rows)

    def test_identity_missing_fields_and_changed_url_types_stop_partial_page_updates(self):
        for changed in ('identity', 'environment', 'missing', 'field-type', 'image-type', 'no-images'):
            document = self.document()
            if changed == 'identity': document['config']['application'] = 'Other'
            if changed == 'environment': document['config']['environment'] = 'preview'
            if changed == 'missing': del document['config']['content']['default']
            if changed == 'field-type': document['config']['orchestrationUrl'] = []
            if changed == 'image-type': document['document']['children'].append({'imageUrl': {}})
            if changed == 'no-images': document['document'] = {'text': 'No image fields'}
            with self.subTest(changed=changed), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.html(document))

    def test_duplicate_truncated_wrong_mime_and_non_object_page_data_are_rejected(self):
        for html in (self.html() + self.html(), self.html().removesuffix('</script>'),
                     self.html().replace('application/json', 'text/javascript'), self.html([]),
                     self.html().replace('"application": "Video"',
                                         '"application": "Other", "application": "Video"'),
                     self.html().replace('"page": "/[[...path]]"', '"page":')):
            with self.subTest(html=html[:80]), self.assertRaises(Invalid):
                extract_rows(self.recipe(), html)

    def test_shared_hosts_are_not_silently_removed_from_the_selected_product_purposes(self):
        document = self.document()
        document['config']['content']['default'] = 'https://storage.shared.example/vendor/file'
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), self.html(document), shared_hosts=['storage.shared.example'])
        document['config']['content']['default'] = 'https://github.io/vendor/file'
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), self.html(document))

    def test_image_parameters_need_an_explicit_field_policy_and_never_enter_rule_rows(self):
        recipe = self.recipe()
        document = self.document()
        document['document']['children'].append({'imageUrl': 'https://images.vendor.example/a.png?width=480'})
        with self.assertRaises(Invalid): extract_rows(recipe, self.html(document))
        recipe['url-fields'][0]['allow-query'] = True
        self.assertIn('DOMAIN,images.vendor.example', extract_rows(recipe, self.html(document)))
        recipe['url-fields'][0]['allow-query'] = 'true'
        with self.assertRaises(Invalid): extract_rows(recipe, self.html(document))

    def test_one_public_page_cannot_authorize_complete_service_inventory_withdrawals(self):
        from loon_rules.generation import inventories
        entry = {'mode': 'compiled', 'extract': [self.recipe()], 'inventory-refresh': True}
        with self.assertRaisesRegex(Invalid, '完整服务域名来源'):
            inventories.validate({'video': entry})

    def test_new_page_hosts_reach_fine_bundle_and_client_outputs_and_bad_sources_write_nothing(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        from loon_rules.exports import publish

        recipe = self.recipe()
        entry = {'id': 'video', 'mode': 'compiled', 'priority': 20, 'section': 'media',
                 'policy-hint': 'global', 'description': '视频', 'boundary': '专用业务入口',
                 'sources': [recipe['source']], 'extract': [recipe]}
        bundle = {'id': 'video-all', 'mode': 'view', 'priority': 10, 'section': 'media',
                  'description': '视频合集', 'boundary': '替代视频细分', 'members': ['video']}
        config = {'schema-version': 2, 'entries': [bundle, entry],
                  'sections': [{'id': 'media', 'title': '影音'}],
                  'critical': {'api.vendor.example': ['video']}, 'shared-negatives': [],
                  'source-inventories': [{'id': 'video-page', 'source': recipe['source'],
                                          'recipe': recipe, 'owners': ['video']}]}
        initial = self.document()
        initial['config']['content']['default'] = 'https://api.vendor.example/content'
        inputs = {recipe['source']: self.html(initial)}
        with TemporaryDirectory() as tmp, patch.object(lib, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
            root = prepare_workspace(tmp)
            (root / 'rules').mkdir()
            entries = lib.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(lib.render_index(config, entries))
            for product in entries.values():
                path = root / 'rules' / lib.rule_filename(product)
                path.write_text(lib.decorate(product, ['DOMAIN,api.vendor.example'], None, '2026-11-20T00:00:00Z'))
            with patch.object(lib.transport, 'download', side_effect=inputs.__getitem__):
                lib.run(); publish(root)
                document = copy.deepcopy(initial)
                document['config']['content']['default'] = 'https://brand-new.other-provider.example/v1'
                document['document']['children'].append({'imageUrl': 'https://new-images.other-provider.example/a.png'})
                inputs[recipe['source']] = self.html(document)
                lib.run(); publish(root)
                for product in (entry, bundle):
                    path = root / 'rules' / lib.rule_filename(product)
                    for host in ('brand-new.other-provider.example', 'new-images.other-provider.example'):
                        self.assertIn('DOMAIN,' + host, lib.rules.read_rules(path.read_text()))
                        self.assertIn(host, (root / 'dist/sing-box' / path.with_suffix('.json').name).read_text())
                    self.assertEqual(path.read_bytes(), path.with_suffix('.list').read_bytes())
                self.assertEqual(lib.run(offline=True), 0)
                for changed in ('identity', 'type', 'truncated'):
                    before = {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                              for p in (root / folder).rglob('*') if p.is_file()}
                    bad = copy.deepcopy(document)
                    if changed == 'identity': bad['config']['application'] = 'Other'
                    if changed == 'type': bad['config']['orchestrationUrl'] = {'url': 'https://unexpected.example'}
                    inputs[recipe['source']] = self.html(bad)
                    if changed == 'truncated': inputs[recipe['source']] = inputs[recipe['source']].removesuffix('</script>')
                    with self.subTest(changed=changed), self.assertRaises(Invalid): lib.run()
                    self.assertEqual(before, {p: p.read_bytes() for folder in ('rules', 'dist', 'data')
                                             for p in (root / folder).rglob('*') if p.is_file()})
