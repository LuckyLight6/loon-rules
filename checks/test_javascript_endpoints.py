"""Official browser SDK methods must discover new endpoints without executing JavaScript."""
from checks.source_fixtures import PublicSourceExamples
from loon_rules.sources.inputs import extract_rows
from loon_rules.rules import Invalid

class JavascriptEndpointPurposes(PublicSourceExamples):
    def test_constructor_methods_follow_new_literal_servers_and_ignore_notes(self):
        recipe={'format':'javascript-method-urls','methods':['buildSingleDomain','buildSplitDomains']}
        body='''throw new Error('Do not execute');
        // X.buildSplitDomains=function(){return new X("https://comment.example/");};
        const note="https://note.example/";
        X.buildSingleDomain=function(){return new X("https://one.vendor.example/","https://one.vendor.example/");};
        X.buildSplitDomains=function(){return new X("https://api.next-vendor.example/","https://events.unlisted.example/");};'''
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,one.vendor.example','DOMAIN,api.next-vendor.example','DOMAIN,events.unlisted.example'})
        for changed in [body.replace('"https://events.unlisted.example/"','location.origin'),body.replace('buildSingleDomain','differentPurpose'),body+'X.buildSplitDomains=function(){return new X("https://other.example");};']:
            with self.assertRaises(Invalid):extract_rows(recipe,changed)
    def test_environment_dictionary_follows_the_live_binding_and_requires_all_fields(self):
        recipe={'format':'javascript-environment-urls','dictionary-field':'defaults','environment':'PRODUCTION',
                'fields':['checkoutBase','snippetBase']}
        body='const live={checkoutBase:"https://new.vendor.example/",snippetBase:"https://new.shared.example/code.js"};'+\
             'const stage={checkoutBase:"https://stage.vendor.example/",snippetBase:"https://stage.shared.example/code.js"};'+\
             'function unrelated(live){return live;} function Environment(){this.env={defaults:((x={})[Env.PRODUCTION]=live,x[Env.STAGING]=stage,x)};}'
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,new.vendor.example','DOMAIN,new.shared.example'})
        clone='const copy=function(){return copy=Object.assign||function(t){for(var e,n=1,o=arguments.length;n<o;n++)for(var r in e=arguments[n])Object.prototype.hasOwnProperty.call(e,r)&&(t[r]=e[r]);return t},copy.apply(this,arguments)};'
        copied=clone+body.replace('[Env.PRODUCTION]=live','[Env.PRODUCTION]=copy({},live)')
        self.assertEqual(extract_rows(recipe,copied),{'DOMAIN,new.vendor.example','DOMAIN,new.shared.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,copied.replace('return t},copy.apply','return different},copy.apply'))

        for changed in [body.replace('snippetBase:"https://new.shared.example/code.js"','snippetBase:chooseServer()',1),
                        body.replace('Env.PRODUCTION','Env.OTHER'),body.replace('const live=','const replacement=')]:
            with self.assertRaises(Invalid):extract_rows(recipe,changed)
    def test_full_url_literal_inventory_includes_environment_endpoints(self):
        recipe={'format':'javascript-url-literals'}
        body='// https://comment.example\nconst x={prod:"https://live.vendor.example/",staging:"https://staging.vendor.example/"};'
        self.assertEqual(extract_rows(recipe,body),{'DOMAIN,live.vendor.example','DOMAIN,staging.vendor.example'})
        with self.assertRaises(Invalid):extract_rows(recipe,body+'const t=`https://${host}/`;')
        with self.assertRaises(Invalid):extract_rows(recipe,body+'const broken={')

    def test_sdk_dependency_cannot_claim_the_path_shared_cloud_root(self):
        from loon_rules.generation.pipeline import lint_content
        with self.assertRaises(Invalid):lint_content('product',['DOMAIN,storage.googleapis.com'])
        lint_content('storage-provider',['DOMAIN,storage.googleapis.com'],allowed_shared=['storage.googleapis.com'])
