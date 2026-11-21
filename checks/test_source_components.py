import json
from datetime import datetime,timedelta,timezone
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples,prepare_workspace


class SourceComponents(PublicSourceExamples):
    def test_internal_source_failure_is_visible_without_exposing_candidate_content(self):
        from loon_rules.generation import pipeline as lib
        entries={'source-overseas':{'id':'source-overseas','description':'海外来源比对'}}
        status={'checked-at':'2026-11-21T00:00:00Z','inputs-read':0,'inputs-requested':1,
                'reviewed-inputs':{'source-overseas':{'state':'unavailable',
                                                    'untrusted-data':'never-print.example'}},
                'source-inventories':{}}
        summary=lib.render_review(status,entries)
        self.assertIn('海外来源比对',summary)
        self.assertIn('来源无法读取',summary)
        self.assertNotIn('never-print.example',summary)

    def test_internal_source_keeps_withdrawal_observation_between_refreshes(self):
        from loon_rules.generation import pipeline as lib
        source='https://rules.vendor.example/overseas.list'
        component={'id':'source-overseas','mode':'managed','description':'海外来源比对',
                   'boundary':'只供生成器比较来源','sources':[source],'kinds':['DOMAIN'],
                   'flags':[],'license':'MIT','policy-hint':'global','reconcile':'confirmed-withdrawals'}
        entry={'id':'overseas-extra','mode':'compiled','priority':675,'section':'overseas',
               'description':'海外补充','boundary':'未由专项覆盖的公开域名','sources':[source],
               'merge-domains':{'include':['source-overseas']},'fallback':True}
        rows=['DOMAIN,service'+str(i)+'.vendor.example' for i in range(25)]
        cfg={'schema-version':2,'entries':[entry],'source-components':[component],
             'sections':[{'id':'overseas','title':'海外补充'}],'critical':{},'shared-negatives':[]}
        start=datetime(2026,11,21,tzinfo=timezone.utc)
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),\
                redirect_stdout(StringIO()),patch.object(lib,'datetime',wraps=datetime) as clock:
            root=Path(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            (root/'data/maintenance-state.json').write_text(json.dumps({
                'component-rules':{'source-overseas':rows},
                'component-metadata':{'source-overseas':{'created-at':'2020-01-01T00:00:00Z',
                                                        'updated-at':'2020-01-01T00:00:00Z'}}}))
            output=root/'rules'/lib.rule_filename(entry)
            output.write_text(lib.decorate(entry,rows,None,'2020-01-01T00:00:00Z'))
            for time in (start,start+timedelta(hours=22)):
                clock.now.return_value=time
                with patch.object(lib.transport,'download',return_value='\n'.join(rows[:-1])):
                    self.assertEqual(lib.run(),0)
            state=json.loads((root/'data/maintenance-state.json').read_text())
            self.assertEqual(state['component-rules']['source-overseas'],rows[:-1])
            self.assertNotIn(rows[-1],lib.rules.read_rules(output.read_text()))
            self.assertEqual(lib.run(offline=True),0)

    def test_source_comparison_input_is_persisted_without_an_extra_subscription(self):
        from loon_rules.generation import pipeline as lib
        source='https://rules.vendor.example/overseas.list'
        component={'id':'source-overseas','mode':'managed','description':'海外来源比对',
                   'boundary':'只供生成器比较来源','sources':[source],'kinds':['DOMAIN-SUFFIX'],
                   'flags':[],'license':'MIT','notice':'source.txt','policy-hint':'global'}
        entry={'id':'overseas-extra','mode':'compiled','priority':675,'section':'overseas',
               'description':'海外补充','boundary':'未由专项覆盖的公开域名','sources':[source],
               'merge-domains':{'include':['source-overseas']},'fallback':True}
        row='DOMAIN-SUFFIX,service.vendor.example'
        cfg={'schema-version':2,'entries':[entry],'source-components':[component],
             'sections':[{'id':'overseas','title':'海外补充'}],
             'critical':{'www.service.vendor.example':['overseas-extra']},'shared-negatives':[]}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=Path(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(cfg)
            (root/'config/catalog.json').write_text(json.dumps(cfg))
            (root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(cfg,entries))
            (root/'data/maintenance-state.json').write_text(json.dumps({'component-rules':{'source-overseas':[row]}}))
            (root/'rules'/lib.rule_filename(entry)).write_text(lib.decorate(entry,[row],None,'2026-01-01T00:00:00Z'))
            with patch.object(lib.transport,'download',side_effect=lambda url:row):
                self.assertEqual(lib.run(),0)
            self.assertEqual([p.name for p in (root/'rules').glob('*.lsr')],['675-overseas-extra.lsr'])
            state=json.loads((root/'data/maintenance-state.json').read_text())
            self.assertEqual(state['component-rules'],{'source-overseas':[row]})
            self.assertEqual(set(state['rules']),{'overseas-extra'})
            self.assertNotIn('source-overseas',cfg['general'])
            self.assertEqual(lib.run(offline=True),0)
