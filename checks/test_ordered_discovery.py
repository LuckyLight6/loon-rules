from loon_rules.generation import discovery
from checks.source_fixtures import PublicSourceExamples
from loon_rules.generation.pipeline import ordered_route


class OrderedDiscovery(PublicSourceExamples):
    def fixture(self):
        source='https://support.vendor.example/network'
        recipe={'format':'purpose-domain-lists','labels':['Content domains:']}
        entry={'section':'ai','discovery':{'inputs':[{'source':source,'family':'vendor',
                'authority':True,'recipe':recipe}]}}
        entries={'account':{'section':'ai'},'product':entry}
        data={'account':['DOMAIN,auth.content.provider.example'],'product':['DOMAIN,api.vendor.example']}
        document='<p>Content domains:</p><ul><li>*.content.provider.example</li></ul>'
        return entries,data,{source:document}

    def test_official_parent_keeps_the_preceding_login_and_serves_other_content(self):
        entries,data,sources=self.fixture();active=['account','product']
        proposals,report=discovery.propose(entries,data,sources,active=active,shared=set())
        self.assertEqual(proposals['product'],['DOMAIN-WILDCARD,*.content.provider.example'])
        data['product']+=proposals['product']
        self.assertEqual(ordered_route('auth.content.provider.example',active,data),'account')
        self.assertEqual(ordered_route('files.content.provider.example',active,data),'product')
        discovery.verify_report(entries,data,report)
        again,state=discovery.propose(entries,data,sources,active=active,shared=set())
        self.assertEqual(again['product'],[])
        self.assertIn('DOMAIN-WILDCARD,*.content.provider.example',state['product']['proofs'])

    def test_a_parent_cannot_take_a_later_specialty_or_overlap_an_existing_parent(self):
        entries,data,sources=self.fixture()
        accepted,_=discovery.domains(entries['product']['discovery'],data['product'],sources,
                                      reserved=data['account'])
        self.assertEqual(accepted,[])
        proposals,_=discovery.propose(entries,data,sources,active=['product','account'],shared=set())
        self.assertEqual(proposals['product'],[])
        for scope in ('DOMAIN-SUFFIX,provider.example','DOMAIN-WILDCARD,*.content.provider.example'):
            data['account']=[scope]
            proposals,_=discovery.propose(entries,data,sources,active=['account','product'],shared=set())
            self.assertEqual(proposals['product'],[])

    def test_community_votes_cannot_relax_an_existing_specialty_boundary(self):
        entries,data,sources=self.fixture();row='DOMAIN-WILDCARD,*.content.provider.example'
        entries['product']['discovery']['inputs']=[{'source':url,'family':family}
            for url,family in [('https://one.example/rules','one'),('https://two.example/rules','two')]]
        proposals,state=discovery.propose(entries,data,{s['source']:row for s in entries['product']['discovery']['inputs']},
                                          active=['account','product'],shared=set())
        self.assertEqual(proposals['product'],[])
        self.assertEqual(state['product']['scope-conflicts'],1)

    def test_preceding_specialties_do_not_authorize_shared_or_private_parent_scopes(self):
        entries,data,sources=self.fixture()
        proposals,_=discovery.propose(entries,data,sources,active=['account','product'],shared={'content.provider.example'})
        self.assertEqual(proposals['product'],[])
        source=next(iter(sources));sources[source]=sources[source].replace('*.content.provider.example','*.github.io')
        data['account']=['DOMAIN,one.github.io']
        proposals,state=discovery.propose(entries,data,sources,active=['account','product'],shared=set())
        self.assertEqual(proposals['product'],[])
        self.assertEqual(state['product']['state'],'invalid')
