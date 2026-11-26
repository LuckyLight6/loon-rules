"""Read actual image requests without claiming CDN backend query parameters."""
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


class SiteImageResources(PublicSourceExamples):
    def recipe(self):
        return {'format': 'site-resource-hosts', 'source': 'https://video.example/',
                'identity': {'scope': 'source-root', 'brand': 'Video'},
                'properties': ['og:image'],
                'image-attributes': ['src', 'srcset', 'data-src', 'data-srcset']}

    def page(self, images=''):
        return ('<link rel="canonical" href="https://video.example/">'
                '<meta property="og:site_name" content="Video">'
                '<meta property="og:url" content="https://video.example/">'
                '<meta property="og:image" content="https://images.vendor.example/share.jpg?host=origin.hidden.example">'
                + images)

    def test_all_declared_image_attributes_follow_actual_request_hosts(self):
        text = self.page('<img src="/local.jpg">'
                         '<img src="https://photo.new-provider.example/a.jpg?host=other.hidden.example">'
                         '<img data-src="https://lazy.new-provider.example/a.jpg">'
                         '<picture><source srcset="https://small.images.example/a.jpg 320w, '
                         'https://large.images.example/a.jpg 1280w"></picture>'
                         '<img data-srcset="https://retina.images.example/a.jpg 2x">'
                         '<video><source srcset="https://unused.video.example/a.jpg 2x"></video>'
                         '<script>const ignored="https://unrelated.example/pixel";</script>'
                         '<template><img src="https://unused.example/a.jpg"></template>')
        self.assertEqual(extract_rows(self.recipe(), text), {
            'DOMAIN,images.vendor.example', 'DOMAIN,video.example',
            'DOMAIN,photo.new-provider.example', 'DOMAIN,lazy.new-provider.example',
            'DOMAIN,small.images.example', 'DOMAIN,large.images.example',
            'DOMAIN,retina.images.example'})

    def test_relative_images_follow_the_document_base_and_reject_ambiguous_bases(self):
        text = self.page('<base href="https://assets.changed.example/images/">'
                         '<img src="photo.jpg">')
        self.assertEqual(extract_rows(self.recipe(), text), {
            'DOMAIN,images.vendor.example', 'DOMAIN,assets.changed.example'})
        for base in ('<base href="http://assets.changed.example/">',
                     '<base href="https://one.example/"><base href="https://two.example/">'):
            with self.subTest(base=base), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.page(base + '<img src="photo.jpg">'))

    def test_image_fragments_do_not_change_the_request_host(self):
        text = self.page('<img src="https://icons.vendor.example/icons.svg#play">'
                         '<img srcset="https://icons.other.example/icons.svg#pause 2x">')
        self.assertEqual(extract_rows(self.recipe(), text), {
            'DOMAIN,images.vendor.example', 'DOMAIN,icons.vendor.example', 'DOMAIN,icons.other.example'})

    def test_srcset_uses_html_number_syntax(self):
        text = self.page('<img srcset="https://images.number.example/a.jpg 0320w, '
                         'https://images.number.example/b.jpg .5x">')
        self.assertEqual(extract_rows(self.recipe(), text), {
            'DOMAIN,images.vendor.example', 'DOMAIN,images.number.example'})
        for descriptor in ('1.x', '1.e2x', '000w', '1e2w'):
            with self.subTest(descriptor=descriptor), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.page('<img srcset="https://invalid.example/a.jpg ' + descriptor + '">'))

    def test_srcset_keeps_commas_inside_urls_and_ignores_inline_placeholders(self):
        text = self.page('<img src="data:image/png;base64,aGVsbG8=">'
                         '<img srcset="https://images.comma.example/a.jpg?crop=1,2,3 320w, '
                         'https://images.second.example/b.jpg 640w">'
                         '<img srcset="data:image/png;base64,aGVsbG8=, '
                         'https://images.fallback.example/c.jpg 2x">')
        self.assertEqual(extract_rows(self.recipe(), text), {
            'DOMAIN,images.vendor.example', 'DOMAIN,images.comma.example',
            'DOMAIN,images.second.example', 'DOMAIN,images.fallback.example'})

    def test_bad_selected_image_fields_stop_instead_of_returning_partial_results(self):
        for image in ('<img src="http://images.example/a.jpg">',
                      '<img src="https://user:example@images.example/a.jpg">',
                      '<img src="https://127.0.0.1/a.jpg">',
                      '<img src="https://one.images.example/a.jpg" src="https://two.images.example/b.jpg">',
                      '<img srcset="https://images.example/a.jpg 0w">',
                      '<img srcset="https://images.example/a.jpg 1x 2x">'):
            with self.subTest(image=image), self.assertRaises(Invalid):
                extract_rows(self.recipe(), self.page(image))
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), self.page('<img src="https://storage.shared.example/a.jpg">'),
                         shared_hosts=['storage.shared.example'])

    def test_attribute_selection_is_explicit_and_old_metadata_only_mode_is_preserved(self):
        for selection in (True, 'src', [], ['onclick'], ['src', 'src']):
            with self.subTest(selection=selection), self.assertRaises(Invalid):
                extract_rows({**self.recipe(), 'image-attributes': selection}, self.page())
        legacy = self.recipe()
        legacy.pop('image-attributes')
        self.assertEqual(extract_rows(legacy, self.page('<img src="https://unselected.example/a.jpg">')),
                         {'DOMAIN,images.vendor.example'})

    def test_source_host_can_remain_with_the_original_product(self):
        recipe = {**self.recipe(), 'exclude-source-host': True}
        self.assertEqual(extract_rows(recipe, self.page('<img src="/local.jpg">')),
                         {'DOMAIN,images.vendor.example'})
        for value in (1, 'yes', None):
            with self.subTest(value=value), self.assertRaises(Invalid):
                extract_rows({**recipe, 'exclude-source-host': value}, self.page())

    def config(self):
        recipe = self.recipe()
        entry = {'id': 'images', 'mode': 'compiled', 'priority': 20, 'section': 'media',
                 'description': '网页图片', 'boundary': '已核实的网页图片请求',
                 'sources': [recipe['source']], 'extract': [{**recipe, 'exclude-source-host': True}]}
        product = {'id': 'product', 'mode': 'compiled', 'priority': 15, 'section': 'media',
                   'description': '产品网站', 'boundary': '产品自有网站',
                   'sources': [recipe['source']], 'include': ['DOMAIN-SUFFIX,video.example']}
        view = {'id': 'media-all', 'mode': 'view', 'priority': 10, 'section': 'media',
                'description': '媒体合集', 'boundary': '替代细分', 'members': ['product', 'images']}
        return {'schema-version': 2, 'entries': [view, product, entry],
                'sections': [{'id': 'media', 'title': '媒体'}],
                'critical': {'images.vendor.example': ['images']},
                'shared-negatives': ['storage.shared.example'],
                'source-inventories': [{'id': 'all-page-images', 'source': recipe['source'],
                                        'recipe': {k: v for k, v in recipe.items() if k != 'source'},
                                        'owners': ['product', 'images']}]}

    def test_image_inventory_cannot_check_a_smaller_attribute_scope(self):
        config = self.config()
        config['source-inventories'][0]['recipe']['image-attributes'] = ['src']
        with self.assertRaises(Invalid):
            pipeline.validate_declarations(config)

    def test_image_inventory_must_check_the_source_host_too(self):
        config = self.config()
        config['source-inventories'][0]['recipe']['exclude-source-host'] = True
        with self.assertRaises(Invalid):
            pipeline.validate_declarations(config)

    def test_new_image_hosts_reach_fine_aggregate_and_all_apps_and_bad_inputs_preserve_files(self):
        config = self.config()
        inputs = {self.recipe()['source']: self.page()}
        with TemporaryDirectory() as temporary, patch.object(pipeline, 'ROOT', prepare_workspace(temporary)), redirect_stdout(StringIO()):
            root = prepare_workspace(temporary)
            (root / 'rules/loon').mkdir(parents=True)
            entries = pipeline.validate_declarations(config)
            (root / 'config/catalog.json').write_text(json.dumps(config))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(config, entries))
            for entry in entries.values():
                initial = ['DOMAIN-SUFFIX,video.example'] if entry['id'] == 'product' else ['DOMAIN,images.vendor.example']
                (root / 'rules/loon' / pipeline.rule_filename(entry)).write_text(pipeline.decorate(
                    entry, initial, None, '2026-11-26T00:00:00Z'))
            with patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__):
                pipeline.run()
                inputs[self.recipe()['source']] = self.page(
                    '<img src="/local.jpg"><img srcset="https://runtime.unprefilled.example/image.jpg?host=origin.hidden.example 2x">')
                pipeline.run()
                publish(root)
                manifest = json.loads((root / 'rules/manifest.json').read_text())
                for key in ('images', 'media-all'):
                    entry = entries[key]
                    path = root / 'rules/loon' / pipeline.rule_filename(entry)
                    rows = pipeline.rules.read_rules(path.read_text())
                    self.assertIn('DOMAIN,runtime.unprefilled.example', rows)
                    self.assertNotIn('DOMAIN,origin.hidden.example', rows)
                    if key == 'images':
                        self.assertNotIn('DOMAIN,video.example', rows)
                    for client, profile in manifest['clients'].items():
                        output = manifest['formats'][profile['format']]['rules'][path.stem]['paths'][client]
                        self.assertIn('runtime.unprefilled.example', (root / output).read_text())
                before = {path: path.read_bytes() for folder in ('rules', 'data')
                          for path in (root / folder).rglob('*') if path.is_file()}
                for image in ('<img src="https://storage.shared.example/a.jpg">',
                              '<img srcset="https://runtime.unprefilled.example/a.jpg 0w">',
                              '<img src="https://replacement.valid.example/a.jpg">'):
                    inputs[self.recipe()['source']] = self.page(image)
                    with self.subTest(image=image), self.assertRaises(Invalid):
                        pipeline.run()
                    self.assertEqual(before, {path: path.read_bytes() for folder in ('rules', 'data')
                                             for path in (root / folder).rglob('*') if path.is_file()})
