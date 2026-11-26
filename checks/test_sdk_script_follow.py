"""Follow the production SDK's current dependency script instead of pinning a previous path."""
from copy import deepcopy
from unittest.mock import Mock
from checks.source_fixtures import PublicSourceExamples
from loon_rules.sources import expansion,sdk_pages
from loon_rules.rules import Invalid

class ProductionScriptFollow(PublicSourceExamples):
    def spec(self):
        return {'method':'next-sdk','source':'https://cdn.vendor.example/sdk.js','source-format':'javascript-environment',
            'asset-roots':['vendor.example'],'max-documents':1,
            'config':{'dictionary-field':'defaults','environment':'PRODUCTION','fields':['apiBase','scriptBase'],'script-field':'scriptBase'},
            'document':{'format':'javascript-method-urls','methods':['buildDefault']},
            'inventory':{'format':'javascript-url-literals'},
            'reviewed-outside':{'DOMAIN,staging.internal-vendor.example':'预发布环境，不属于生产请求'}}
    def parent(self,url):
        return 'const live={apiBase:"https://api.vendor.example/",scriptBase:"'+url+'"};function Config(){this.env={defaults:((x={})[Env.PRODUCTION]=live,x)};}'
    def child(self,extra=''):
        return 'Client.buildDefault=function(){return new Client("https://legacy.shared.example/"'+extra+');}; const staging="https://staging.internal-vendor.example/";'
    def test_a_new_unlisted_script_path_and_host_are_followed_and_fully_checked(self):
        spec=self.spec();entry={'id':'service','mode':'compiled','sources':[spec['source']],'expand':spec};entries={'service':entry}
        downloaded={spec['source']:self.parent('https://assets.vendor.example/v1.js')}
        fetch=Mock(return_value=self.child())
        rows,report,children=expansion.collect(entries,downloaded,fetch)
        self.assertEqual(fetch.call_args.args[0],'https://assets.vendor.example/v1.js')
        self.assertIn('DOMAIN,legacy.shared.example',rows['service'])
        expansion.verify_report(entries,{'service':['DOMAIN-SUFFIX,vendor.example',*rows['service']]},report)
        downloaded[spec['source']]=self.parent('https://new-assets.vendor.example/v2/current.js')
        fetch=Mock(return_value=self.child(',"https://unseeded.third.example/"'))
        rows,report,children=expansion.collect(entries,downloaded,fetch)
        self.assertEqual(fetch.call_args.args[0],'https://new-assets.vendor.example/v2/current.js')
        self.assertIn('DOMAIN,unseeded.third.example',rows['service'])
        expansion.verify_report(entries,{'service':['DOMAIN-SUFFIX,vendor.example',*rows['service']]},report)
        fetch=Mock(return_value=self.child()+'const unknown="https://unreviewed.third.example/";')
        rows,report,_=expansion.collect(entries,downloaded,fetch)
        with self.assertRaises(Invalid):expansion.verify_report(entries,{'service':['DOMAIN-SUFFIX,vendor.example',*rows['service']]},report)
        bad=deepcopy(report);bad['service']['documents'][0]['source']='https://assets.vendor.example/old.js'
        with self.assertRaises(Invalid):sdk_pages.verify(spec,bad['service'])
