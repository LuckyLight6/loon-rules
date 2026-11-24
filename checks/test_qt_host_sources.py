"""Read exact product hosts from explicit Qt URL predicates, without running code."""
from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class QtHostSources(PublicSourceExamples):
    def recipe(self):
        return {'format': 'qt-host-predicate', 'function': 'IsProductHost'}

    def body(self):
        return '''
// A link allowlist elsewhere may contain unrelated providers.
QStringList OtherLinks() { return {u"other-provider.example"_q}; }
bool IsProductHost(const QUrl &url) {
    const auto host = url.host().toLower();
    return (host == u"product.example"_q)
        || (host == u"files.provider.example"_q);
}
'''

    def test_only_the_named_exact_host_predicate_supplies_domains(self):
        from loon_rules.sources.formats import READERS
        self.assertIn('qt-host-predicate', READERS)
        self.assertEqual(extract_rows(self.recipe(), self.body()),
                         {'DOMAIN,product.example', 'DOMAIN,files.provider.example'})
        changed = self.body().replace('u"files.provider.example"_q',
                                      'u"new-service.example"_q')
        self.assertEqual(extract_rows(self.recipe(), changed),
                         {'DOMAIN,product.example', 'DOMAIN,new-service.example'})

    def test_changed_meaning_or_incomplete_code_does_not_publish_partial_hosts(self):
        for body in (self.body().replace('||', '&&'),
                     self.body().replace('url.host()', 'url.path()'),
                     self.body().replace('const QUrl &url', 'const QString &url'),
                     self.body().replace('host ==', 'host !='),
                     self.body().replace('product.example', '*.product.example'),
                     self.body().replace('product.example', 'co.uk'),
                     self.body().replace('u"files.provider.example"_q', 'dynamicHost()'),
                     self.body() + self.body(), self.body()[:-2]):
            with self.subTest(body=body), self.assertRaises(Invalid):
                extract_rows(self.recipe(), body)

    def test_declared_shared_endpoints_cannot_be_silently_filtered_from_the_function(self):
        with self.assertRaises(Invalid):
            extract_rows(self.recipe(), self.body(), shared_hosts=['files.provider.example'])

    def test_missing_function_and_injected_declaration_are_rejected(self):
        with self.assertRaises(Invalid):
            extract_rows({**self.recipe(), 'function': 'IsOtherProduct'}, self.body())
        with self.assertRaises(Invalid):
            extract_rows({**self.recipe(), 'function': 'IsProductHost();'}, self.body())

    def test_publishing_a_predicate_requires_the_same_complete_function_inventory(self):
        from loon_rules.generation import pipeline
        recipe = {**self.recipe(), 'source': 'https://vendor.example/client.cpp'}
        entry = {'id': 'product', 'priority': 20, 'mode': 'compiled', 'section': 'products',
                 'description': '产品', 'boundary': '指定用途函数', 'sources': [recipe['source']],
                 'extract': [recipe]}
        config = {'schema-version': 2, 'entries': [entry], 'critical': {}, 'shared-negatives': [],
                  'sections': [{'id': 'products', 'title': '产品'}]}
        with self.assertRaisesRegex(Invalid, '完整|归属'):
            pipeline.validate_declarations(config)
        spec = {'id': 'complete-function', 'source': recipe['source'], 'owners': ['product'],
                'recipe': self.recipe()}
        config['source-inventories'] = [spec]
        pipeline.validate_declarations(config)
        spec['recipe'] = {**self.recipe(), 'function': 'OtherFunction'}
        with self.assertRaises(Invalid):
            pipeline.validate_declarations(config)
