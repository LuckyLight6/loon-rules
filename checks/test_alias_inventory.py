from checks.source_fixtures import prepare_workspace
import copy
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks.source_fixtures import PublicSourceExamples
from loon_rules.rules import Invalid


class CnameAliasInventory(PublicSourceExamples):
    def evidence_fixture(self):
        host='download.vendor.example';alias='product-download.github.io'
        entries={'download':{'priority':30,'mode':'compiled','aliases':{
            'policy':'vendor','sources':[],'resolve-cname':True}}}
        policies={'vendor':{'parents':{'vendor.example':['vendor.example.delivery.example']},
                           'label-modifiers':['lb'],'cname-tenants':{'vendor.example':['github.io']}}}
        proof={'download':{'DOMAIN,'+alias:{'canonical-hosts':[host],'state':'current'}}}
        data={'download':['DOMAIN,'+host]}
        published={'download':['DOMAIN,'+host,'DOMAIN,'+alias]}
        return host,alias,entries,policies,proof,data,published

    def test_successful_queries_unrelated_failures_and_disabled_queries_do_not_retain_old_aliases(self):
        from loon_rules.sources import aliases as source_aliases
        host,alias,entries,policies,proof,data,published=self.evidence_fixture()
        for records,queried in (({host:[]},{host}),({}, {'unrelated.vendor.example'})):
            with self.subTest(records=records,queried=queried):
                candidate=copy.deepcopy(data);current={}
                self.assertEqual(source_aliases.reconcile(entries,candidate,current,proof,published,policies,
                    queried=queried,records=records,order=['download']),{})
                self.assertEqual(candidate,{'download':['DOMAIN,'+host]})
                self.assertEqual(current,{})
        entries['download']['aliases']['resolve-cname']=False
        self.assertEqual(source_aliases.reconcile(entries,data,{},proof,published,policies,
            queried={host},records={},order=['download']),{})

    def test_history_cannot_admit_an_unpublished_alias(self):
        from loon_rules.sources import aliases as source_aliases
        host,alias,entries,policies,proof,data,published=self.evidence_fixture()
        with self.assertRaises(Invalid):source_aliases.reconcile(entries,data,{},proof,data,policies,
            queried={host},records={},order=['download'])

    def test_offline_evidence_rejects_wider_scopes_other_services_and_unknown_fields(self):
        from loon_rules.sources import aliases as source_aliases
        host,alias,entries,policies,proof,data,published=self.evidence_fixture()
        source_aliases.verify_evidence(entries,published,proof,policies,order=['download'])
        for row,record in [('DOMAIN-SUFFIX,'+alias,proof['download']['DOMAIN,'+alias]),
                           ('DOMAIN,'+alias,{'canonical-hosts':['unrelated.other.example'],'state':'current'}),
                           ('DOMAIN,'+alias,{'canonical-hosts':[host],'state':'current','candidates':['unselected.example']})]:
            with self.subTest(row=row,record=record),self.assertRaises(Invalid):
                source_aliases.verify_evidence(entries,published,{'download':{row:record}},policies,order=['download'])

    def test_dns_evidence_and_required_host_protection_survive_compacted_membership(self):
        from loon_rules.generation import pipeline as lib
        host='download.vendor.example';alias='download.vendor.example.delivery.example'
        entry={'mode':'compiled','priority':30,'aliases':{'policy':'vendor','sources':[],
               'resolve-cname':True,'protect-from-reject':True}}
        config={'detailed':['download'],'general':[],'source-alias-policies':{'vendor':{
            'parents':{'vendor.example':['vendor.example.delivery.example']},'label-modifiers':['lb']}}}
        data={'download':['DOMAIN,'+host,'DOMAIN-SUFFIX,'+alias]};proof={}
        lib.apply_source_aliases(config,{'download':entry},data,{},dns_records={host:[alias]},dns_evidence=proof)
        self.assertEqual(proof,{'download':{'DOMAIN,'+alias:{'canonical-hosts':[host],'state':'current'}}})
        self.assertIn(alias,lib.functional_hostnames({'download':entry},{},dns_evidence=proof))

    def test_refresh_keeps_proven_aliases_during_lookup_failure_and_recovers_their_evidence(self):
        from loon_rules.generation import pipeline as lib
        host='download.vendor.example';alias='product-download.github.io'
        entry={'id':'download','mode':'compiled','priority':30,'section':'service',
               'description':'下载','boundary':'产品下载','sources':['https://vendor.example/network'],
               'include':['DOMAIN,'+host],
               'aliases':{'policy':'vendor','sources':[],'resolve-cname':True,'protect-from-reject':True}}
        config={'schema-version':2,'entries':[entry],
                'sections':[{'id':'service','title':'服务'}],
                'critical':{host:['download'],alias:['download']},'shared-negatives':[],
                'source-alias-policies':{'vendor':{
                    'parents':{'vendor.example':['vendor.example.delivery.example']},
                    'label-modifiers':['lb'],'cname-tenants':{'vendor.example':['github.io']}}}}
        intermediate='download.vendor.example.delivery.example'
        current={host:[intermediate,alias]};incomplete=[]
        def collect(names,**kwargs):
            return copy.deepcopy(current),{'hosts-requested':len(names),'hosts-read':len(current),
                'http-requests':2*len(names),'unavailable-hosts':len(names)-len(current),
                'unavailable-lookups':len(names)-len(current)+len(incomplete),
                'incomplete-hosts':incomplete.copy()}
        with TemporaryDirectory() as tmp,patch.object(lib,'ROOT',prepare_workspace(tmp)),redirect_stdout(StringIO()):
            root=prepare_workspace(tmp);(root/'rules').mkdir();entries=lib.validate_declarations(config)
            path=root/'rules'/lib.rule_filename(entry)
            path.write_text(lib.decorate(entry,['DOMAIN,'+host],None,'2020-01-01T00:00:00Z'))
            (root/'config/catalog.json').write_text(json.dumps(config));(root/'config/endpoint-contracts.json').write_text('[]')
            (root/'docs/rules.md').write_text(lib.render_index(config,entries))
            with patch.object(lib.source_dns,'collect',side_effect=collect):
                lib.run()
                first=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertIn('DOMAIN,'+alias,lib.rules.read_rules(path.read_text()))
                forged=copy.deepcopy(first);forged['cname-alias-evidence']={}
                (root/'data/maintenance-state.json').write_text(json.dumps(forged))
                (root/'build/verification.md').write_text(lib.render_review(forged,entries))
                with self.assertRaises(Invalid):lib.run(offline=True)
                (root/'data/maintenance-state.json').write_text(json.dumps(first))
                (root/'build/verification.md').write_text(lib.render_review(first,entries))
                current.clear()
                lib.run()
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertIn('DOMAIN,'+alias,lib.rules.read_rules(path.read_text()))
                self.assertIn(alias,report['functional-hosts'])
                proof=report['cname-alias-evidence']['download']['DOMAIN,'+alias]
                self.assertEqual(proof,{'canonical-hosts':[host],'state':'retained'})
                self.assertEqual(first['cname-alias-evidence']['download']['DOMAIN,'+alias]['state'],'current')
                self.assertEqual(lib.run(offline=True),0)
                current[host]=[intermediate];incomplete.append(host);lib.run()
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['cname-alias-evidence']['download']['DOMAIN,'+alias]['state'],'retained')
                self.assertIn('DOMAIN,'+alias,lib.rules.read_rules(path.read_text()))
                incomplete.clear();current[host]=[intermediate,alias];lib.run()
                report=json.loads((root/'data/maintenance-state.json').read_text())
                self.assertEqual(report['cname-alias-evidence']['download']['DOMAIN,'+alias]['state'],'current')
                current[host]=[]
                snapshot={p:p.read_text() for p in root.rglob('*') if p.is_file()}
                with self.assertRaises(Invalid):lib.run()
                self.assertEqual(snapshot,{p:p.read_text() for p in root.rglob('*') if p.is_file()})
