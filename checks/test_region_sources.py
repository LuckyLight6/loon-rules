from loon_rules.rules import Invalid
from loon_rules.sources.inputs import extract_rows
from checks.source_fixtures import PublicSourceExamples


class RegionEndpointSources(PublicSourceExamples):
    def fixture(self):
        return {'format':'region-endpoint-table', 'headers':[['Region','API','Compatible API']],
                'regions':{'mainland':r'^China \((?!Hong Kong|Macao|Taiwan)[A-Za-z -]+\)$',
                           'international':r'^(?:China \((?:Hong Kong|Macao|Taiwan)\)|(?!China\b)[A-Za-z][A-Za-z ()-]*)$'},
                'region':'mainland', 'roots':['api.vendor.example'],
                'workspace-parent':'workspaces.vendor.example',
                'workspace-prefixes':['{workspaceid}','trial','token-plan']}

    def table(self, rows):
        return '<h2 id="api">Endpoints</h2><table>'+''.join(
            '<tr>'+''.join('<td>'+v+'</td>' for v in row)+'</tr>'
            for row in [['Region','API','Compatible API'],*rows])+'</table>'

    def test_new_region_hosts_are_discovered_from_their_row_without_name_lists(self):
        recipe=self.fixture()
        text=self.table([
            ['China (New City)','https://new-cn.api.vendor.example/v1','https://{WorkspaceId}.new-cn.workspaces.vendor.example/v1'],
            ['New Country','https://new-world.api.vendor.example/v1','https://trial.new-world.workspaces.vendor.example/v1'],
            ['China (Hong Kong)','https://hk.api.vendor.example/v1','https://token-plan.hk.workspaces.vendor.example/v1']])
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,new-cn.api.vendor.example',
                         'DOMAIN-SUFFIX,new-cn.workspaces.vendor.example'})
        recipe['region']='international'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,new-world.api.vendor.example','DOMAIN,hk.api.vendor.example',
                         'DOMAIN-SUFFIX,new-world.workspaces.vendor.example','DOMAIN-SUFFIX,hk.workspaces.vendor.example'})

    def test_unknown_region_and_unrelated_hosts_stop_the_region_import(self):
        recipe=self.fixture()
        for row in (['Unknown 123','https://cn.api.vendor.example','https://cn.api.vendor.example'],
                    ['China (Beijing)','https://unrelated.example','https://cn.api.vendor.example']):
            with self.subTest(row=row),self.assertRaises(Invalid):extract_rows(recipe,self.table([row]))

    def test_plain_host_fields_and_financial_sections_use_the_same_region_logic(self):
        recipe={'format':'region-endpoint-table','headers':[['接入地域','域名'],['金融区接入地域','金融区域名']],
                'regions':{'mainland':r'^(?:华|西|东|就近).+', 'international':r'^(?:港澳台|欧洲|亚太).+'},
                'region':'mainland','roots':['cloudapi.example'],'bare-hosts':True}
        text='<table><tr><td>接入地域</td><td>域名</td></tr><tr><td>华南（新城市）</td><td>new.cloudapi.example</td></tr>'
        text+='<tr><td>欧洲（新城市）</td><td>eu.cloudapi.example</td></tr><tr><td>金融区接入地域</td><td>金融区域名</td></tr>'
        text+='<tr><td>华东（新金融区）</td><td>fsi.cloudapi.example</td></tr></table>'
        self.assertEqual(extract_rows(recipe,text),{'DOMAIN,new.cloudapi.example','DOMAIN,fsi.cloudapi.example'})

    def test_a_shared_api_parent_still_requires_the_product_service_label(self):
        recipe=self.fixture()
        recipe.update(roots=['vendor.example'], **{'host-pattern':r'api\.[a-z-]+\.vendor\.example'})
        text=self.table([['China (Beijing)','https://api.new-cn.vendor.example','https://other.vendor.example']])
        with self.assertRaises(Invalid):extract_rows(recipe,text)
