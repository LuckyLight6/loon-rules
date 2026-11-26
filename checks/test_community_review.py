"""A changed source must not replace a previous complete observation with a partial one."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import hashlib
import unittest
from unittest.mock import patch
from loon_rules.community_review import run

class CommunityReviewLifecycle(unittest.TestCase):
    def test_whole_input_drift_and_invalid_followup_keep_the_previous_source(self):
        with TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'config').mkdir();(root/'rules/loon').mkdir(parents=True);(root/'data').mkdir()
            source={'id':'public-service','repository':'public/rules','ref':'release','path':'service.list','format':'classical','products':['service']}
            (root/'config/community-sources.json').write_text(json.dumps({'schema-version':1,'inputs':[source],'queries':[]}))
            (root/'config/catalog.json').write_text(json.dumps({'schema-version':2,'sections':[{'id':'products','title':'产品'}],'entries':[{'id':'service','mode':'compiled','priority':10,'section':'products','description':'产品','boundary':'专用服务','sources':['https://vendor.example/'],'include':['DOMAIN-SUFFIX,service.example']}],'critical':{},'shared-negatives':[]}))
            (root/'rules/loon/010-service.lsr').write_text('DOMAIN-SUFFIX,service.example\n')
            revision=['a'*40];body=['DOMAIN-SUFFIX,service.example\n']
            history={}
            builder=[b'build_from_declared_inputs()\n']
            def resolver(repository,ref):
                history[revision[0]]=body[0].encode()
                return {'revision':revision[0],'committed-at':'2026-11-27T00:00:00Z'}
            def download(url):return builder[0] if url.endswith('/build.py') else history[url.split('/')[5]]
            with patch('loon_rules.community_review.resolve',side_effect=resolver),patch('loon_rules.community_review.download',side_effect=download):
                result=run(root,search=False)
                self.assertEqual(result['inputs-normalized'],1)
                previous=json.loads((root/'data/community-state.json').read_text())
                revision[0]='b'*40;body[0]+='DOMAIN,not-in-service.example\n'
                result=run(root,search=False)
                self.assertEqual(result['inputs-with-changes'],1)
                report=json.loads((root/'build/community-review/report.json').read_text())
                self.assertIn('DOMAIN,not-in-service.example',report['inputs'][0]['changes']['added'])
                accepted=json.loads((root/'data/community-state.json').read_text())
                revision[0]='c'*40;body[0]+='UNKNOWN,unreadable.example\n'
                result=run(root,search=False)
                self.assertEqual(result['inputs-held'],1)
                current=json.loads((root/'data/community-state.json').read_text())
                self.assertEqual(current['inputs']['public-service'],accepted['inputs']['public-service'])
                self.assertEqual((root/'rules/loon/010-service.lsr').read_text(),'DOMAIN-SUFFIX,service.example\n')

                registry=json.loads((root/'config/community-sources.json').read_text())
                registry['inputs'].append({**source,'id':'declared-parent'})
                registry['inputs'][0]['upstream-inputs']=['declared-parent']
                registry['inputs'][0]['lineage-proof']={'path':'build.py','sha256':hashlib.sha256(builder[0]).hexdigest()}
                (root/'config/community-sources.json').write_text(json.dumps(registry))
                revision[0]='d'*40;body[0]='DOMAIN-SUFFIX,service.example\n'
                result=run(root,search=False)
                self.assertEqual(result['inputs-held'],0)
                good=json.loads((root/'data/community-state.json').read_text())['inputs']['public-service']
                revision[0]='e'*40;builder[0]=b'build_from_different_inputs()\n'
                result=run(root,search=False)
                self.assertEqual(result['inputs-held'],1)
                current=json.loads((root/'data/community-state.json').read_text())['inputs']['public-service']
                self.assertEqual(current,good)
