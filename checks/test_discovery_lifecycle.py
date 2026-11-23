from checks.source_fixtures import prepare_workspace
from contextlib import redirect_stdout
from datetime import datetime,timedelta,timezone
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples
from loon_rules.generation import pipeline as lib


class DiscoveryLifecycle(PublicSourceExamples):
    def test_compiled_discovery_failure_stops_publication_even_when_the_parent_still_matches(self):
        feed = 'https://public.example/product.rules'
        sdk = 'https://public.example/product.sdk'
        entry = {
            'id': 'product', 'mode': 'compiled', 'priority': 30, 'section': 'service',
            'description': '产品', 'boundary': '业务入口', 'sources': [feed, sdk],
            'projection': [{'source': feed, 'roots': ['vendor.example']}],
            'discovery': {'inputs': [{
                'source': sdk, 'family': 'vendor', 'authority': True,
                'recipe': {'format': 'python-sdk-endpoints', 'module-level': True,
                           'fields': ['API_ENDPOINT']},
            }]},
        }
        config = {'schema-version': 2, 'entries': [entry], 'critical': {},
                  'shared-negatives': [], 'sections': [{'id': 'service', 'title': '服务'}]}
        for failure in ('invalid', 'unavailable'):
            with self.subTest(failure=failure), TemporaryDirectory() as tmp, \
                    patch.object(lib, 'ROOT', prepare_workspace(tmp)), redirect_stdout(StringIO()):
                root = prepare_workspace(tmp)
                (root / 'rules').mkdir()
                (root / 'config/endpoint-contracts.json').write_text('[]')
                entries = lib.validate_declarations(config)
                (root / 'config/catalog.json').write_text(json.dumps(config))
                (root / 'docs/rules.md').write_text(lib.render_index(config, entries))
                output = root / 'rules' / lib.rule_filename(entry)
                output.write_text(lib.decorate(entry, ['DOMAIN-SUFFIX,vendor.example'],
                                                None, '2020-01-01T00:00:00Z'))
                downloads = {feed: 'DOMAIN-SUFFIX,vendor.example',
                             sdk: 'API_ENDPOINT="https://api.vendor.example"'}

                def read(url):
                    if url not in downloads:
                        raise lib.rules.Invalid('official source unavailable')
                    return downloads[url]

                with patch.object(lib.transport, 'download', side_effect=read):
                    lib.run()
                    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
                    if failure == 'invalid':
                        downloads[sdk] = 'UNRELATED="https://other.example"'
                    else:
                        downloads.pop(sdk)
                    with self.assertRaisesRegex(lib.rules.Invalid, '自动发现来源'):
                        lib.run()
                    self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})
                    downloads[sdk] = 'API_ENDPOINT="https://api.new-provider.example"'
                    lib.run()
                    self.assertIn('DOMAIN,api.new-provider.example',
                                  lib.rules.read_rules(output.read_text()))

    def test_failed_official_input_cannot_retire_a_published_endpoint_or_its_protection(self):
        feed='https://public.example/rules';sdk='https://public.example/sdk'
        endpoint='DOMAIN,api.product.example'
        baseline=['DOMAIN-SUFFIX,base'+str(i)+'.vendor.example' for i in range(50)]
        entry={'id':'product','mode':'managed','priority':30,'section':'service','selection':'detailed',
               'description':'产品','boundary':'官方 API','sources':[feed,sdk],'feed-sources':[feed],
               'kinds':['DOMAIN-SUFFIX'],'flags':[],'license':'MIT','reconcile':'confirmed-withdrawals',
               'discovery':{'inputs':[{'source':sdk,'family':'vendor','authority':True,
                   'recipe':{'format':'python-sdk-endpoints','module-level':True,'fields':['API_ENDPOINT']}}]}}
        config={'schema-version':2,'entries':[entry],'critical':{},'shared-negatives':[],
                'sections':[{'id':'service','title':'服务'}]}
        valid='API_ENDPOINT="https://api.product.example/v1"'
        for failure in ('invalid','unavailable'):
            with self.subTest(failure=failure),TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),\
                    redirect_stdout(StringIO()),patch.object(lib,'datetime',wraps=datetime) as clock:
                start=datetime(2026,11,21,tzinfo=timezone.utc);clock.now.return_value=start
                root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(config)
                (root/'config/catalog.json').write_text(json.dumps(config));(root/'config/endpoint-contracts.json').write_text('[]')
                (root/'docs/rules.md').write_text(lib.render_index(config,entries));output=root/'rules'/lib.rule_filename(entry)
                output.write_text(lib.decorate(entry,baseline,None,'2020-01-01T00:00:00Z'))
                downloads={feed:'\n'.join(baseline),sdk:valid}
                def read(url):
                    if url==sdk and sdk not in downloads:raise lib.rules.Invalid('official source unavailable')
                    return downloads[url]
                with patch.object(lib.transport,'download',side_effect=read):
                    lib.run();self.assertIn(endpoint,lib.rules.read_rules(output.read_text()))
                    previous=json.loads((root/'data/maintenance-state.json').read_text())
                    previous['functional-hosts'].append('unrelated.other.example')
                    (root/'data/maintenance-state.json').write_text(json.dumps(previous))
                    if failure=='invalid':downloads[sdk]='UNRELATED="https://other.example"'
                    else:downloads.pop(sdk)
                    for hours in (1,22):
                        clock.now.return_value=start+timedelta(hours=hours);lib.run()
                    self.assertIn(endpoint,lib.rules.read_rules(output.read_text()))
                    status=json.loads((root/'data/maintenance-state.json').read_text())
                    self.assertEqual(status['discovery']['product']['state'],failure)
                    self.assertEqual(status['reviewed-inputs']['product']['state'],failure)
                    self.assertIn('api.product.example',status['functional-hosts'])
                    self.assertNotIn('unrelated.other.example',status['functional-hosts'])
                    self.assertNotIn('withdrawal-observation',status['reviewed-inputs']['product'])
                    changed=json.loads((root/'config/catalog.json').read_text())
                    changed['entries'][0]['excluded-rules']=[baseline[0]]
                    (root/'config/catalog.json').write_text(json.dumps(changed));lib.run()
                    self.assertNotIn(baseline[0],lib.rules.read_rules(output.read_text()))
                    self.assertIn(endpoint,lib.rules.read_rules(output.read_text()))
                    downloads[sdk]=valid;clock.now.return_value=start+timedelta(hours=23);lib.run()
                    self.assertEqual(json.loads((root/'data/maintenance-state.json').read_text())['discovery']['product']['state'],'current')
                    self.assertEqual(lib.run(offline=True),0)
