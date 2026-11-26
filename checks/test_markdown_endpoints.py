from checks.source_fixtures import prepare_workspace
from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows


class MarkdownEndpoints(PublicSourceExamples):
    def recipe(self):
        return {'format':'markdown-purpose-endpoints','section':'General API information',
                'label-contains':'base endpoint','schemes':['https','wss']}

    def document(self):
        return '''# Public API
## General API information
- The following base endpoints are available:
  - **https://api.vendor.example**
  - **https://new-api.other.example/v2**
- For public data, use the base endpoint
  `https://data.vendor.example`.
- The base endpoint is **wss://socket.vendor.example:9443/ws**.
- Read [the docs](https://docs.unrelated.example) for details.
```text
- The base endpoint is **https://payload.unrelated.example**.
```
<!-- - The base endpoint is **https://comment.unrelated.example**. -->
## Other product
- The base endpoint is **https://other-product.unrelated.example**.
'''

    def test_endpoint_bullets_and_continuations_ignore_navigation_examples_and_other_sections(self):
        self.assertEqual(extract_rows(self.recipe(),self.document()),{
            'DOMAIN,api.vendor.example','DOMAIN,new-api.other.example',
            'DOMAIN,data.vendor.example','DOMAIN,socket.vendor.example'})

    def test_source_can_add_a_new_host_without_a_name_selector(self):
        doc=self.document().replace('  - **https://api.vendor.example**',
            '  - **https://unlisted.new-provider.example**')
        rows=extract_rows(self.recipe(),doc)
        self.assertIn('DOMAIN,unlisted.new-provider.example',rows)
        self.assertNotIn('DOMAIN,api.vendor.example',rows)

    def test_missing_or_duplicate_sections_and_unlabelled_urls_are_not_accepted(self):
        for doc in (self.document().replace('## General API information','## Other information'),
                    self.document()+'\n## General API information\n- The base endpoint is **https://api.vendor.example**.',
                    self.document().replace('base endpoint','ordinary link')):
            with self.subTest(doc=doc[:80]),self.assertRaises(Invalid):extract_rows(self.recipe(),doc)

    def test_endpoint_fields_reject_credentials_private_names_and_unexpected_protocols(self):
        for url in ('https://reader@api.vendor.example','https://127.0.0.1',
                    'https://server.internal','ftp://api.vendor.example',
                    'https://api.vendor.example?token=value'):
            doc=self.document().replace('https://api.vendor.example',url)
            with self.subTest(url=url),self.assertRaises(Invalid):extract_rows(self.recipe(),doc)

    def test_an_unlisted_server_reaches_the_subscription_and_survives_repeated_refresh(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from loon_rules.generation import pipeline as lib
        source='https://docs.vendor.example/api'
        entry={'id':'product','mode':'compiled','priority':30,'section':'service','selection':'detailed',
               'description':'产品接口','boundary':'服务端点','sources':[source],
               'extract':[{**self.recipe(),'source':source}]}
        cfg={'schema-version':2,'entries':[entry],'critical':{'api.vendor.example':['product']},
             'shared-negatives':[],'sections':[{'id':'service','title':'服务'}],
             'routing-bands':[{'start':30,'title':'服务'}]}
        first='## General API information\n- The base endpoint is **https://api.vendor.example**.'
        documents={source:first}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules' / 'loon').mkdir(parents=True, exist_ok=True);entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            output=root/'rules' / 'loon'/lib.rule_filename(entry)
            output.write_text(lib.decorate(entry,['DOMAIN,api.vendor.example'],None,'2026-11-20T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=documents.__getitem__):
                lib.run()
                documents[source]=first+'\n- The public base endpoint is **wss://unlisted.new-provider.example**.'
                lib.run();lib.run()
            rows=lib.rules.read_rules(output.read_text())
            self.assertIn('DOMAIN,unlisted.new-provider.example',rows)
            self.assertEqual(lib.run(offline=True),0)
