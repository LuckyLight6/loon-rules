"""A hosted source must not mix metadata and artifacts from different builds."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from loon_rules.community_web import watch

class HostedCommunityVersions(unittest.TestCase):
    def test_one_mismatched_artifact_holds_the_whole_previous_build(self):
        spec={'id':'hosted','url':'https://rules.example/','metadata':'https://rules.example/geosite-meta',
              'artifacts':[{'id':'strict','url':'https://rules.example/strict/ai','format':'classical','products':[]},
                           {'id':'balanced','url':'https://rules.example/balanced/ai','format':'classical','products':[]}]}
        tag='20261126000000'
        responses={spec['metadata']:(json.dumps({'schema':2,'tag':tag,'stats':{'lists':1},'lists':[{'name':'ai'}]}).encode(),None),
                   spec['artifacts'][0]['url']:(b'DOMAIN,service.example\n',tag),
                   spec['artifacts'][1]['url']:(b'DOMAIN,service.example\n',tag)}
        with TemporaryDirectory() as temporary,patch('loon_rules.community_web.get',side_effect=lambda url:responses[url]):
            report,accepted=watch([spec],{},Path(temporary))
            self.assertEqual(report[0]['state'],'complete-build-for-review')
            previous=accepted.copy()
            responses[spec['artifacts'][1]['url']]=(b'DOMAIN,other.example\n','20261125000000')
            report,accepted=watch([spec],previous,Path(temporary))
            self.assertEqual(report[0]['state'],'held')
            self.assertEqual(accepted,previous)
            responses[spec['artifacts'][1]['url']]=(b'DOMAIN,other.example\nUNKNOWN,bad.example\n',tag)
            report,accepted=watch([spec],previous,Path(temporary))
            self.assertEqual(report[0]['state'],'held')
            self.assertEqual(accepted,previous)
