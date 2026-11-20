import unittest
from rule_inputs import extract_rows
import endpoint_contracts as ec
import library as lib

class RoleUpdates(unittest.TestCase):
    def test_windows_table_is_scoped_by_product_role_and_column(self):
        spec={'format':'windows-purpose','section':'connection','product':'Xbox Live',
              'purpose':['used for xbox live'], 'roots':['xbox.example']}
        def row(*v):return '<tr>'+''.join('<td>'+x+'</td>' for x in v)+'</tr>'
        text='<h2 id="connection">Endpoints</h2><table>'+''.join([
            row('Xbox Live','','','Setup instructions'),row('','These servers are used for Xbox Live','TLS','one.xbox.example'),
            row('','','TLS','new.xbox.example'),row('','diagnostics','TLS','stats.xbox.example'),
            row('Other','','',''),row('','','TLS','wrong.xbox.example')])+'</table>'
        self.assertEqual(extract_rows(spec,text),{'DOMAIN,one.xbox.example','DOMAIN,new.xbox.example'})

    def test_authoritative_host_does_not_import_its_upstream_parent_or_shared_siblings(self):
        e={'id':'a','sources':['feed'],'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[],'official-hosts':True}
        old=['DOMAIN,login.a.example']
        feed=old+['DOMAIN-SUFFIX,cdn.example','DOMAIN,noise.example']
        out,_=lib.refresh_reviewed_feed(e,old,{'feed':'\n'.join(feed)},official=['new.cdn.example'])
        self.assertEqual(set(out),{old[0],'DOMAIN,new.cdn.example'})
        again,_=lib.refresh_reviewed_feed(e,out,{'feed':'\n'.join(feed)},official=['new.cdn.example'])
        self.assertEqual(out,again)

    def test_new_claude_delivery_hostname_needs_named_purpose_and_direct_feed_evidence(self):
        from copy import deepcopy
        contract={'id':'code','format':'claude-code-table','source':'official','routes':{'claude':['claude.example']},
                  'discover':{'claude':{'roots':['claude.example'],'feed-and-purpose':['native installer']}},
                  'unassigned':'hold'}
        entries={'claude':{'id':'claude','feed-sources':['feed'],'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[]}}
        src={'official':'## Network access requirements\n\n| URL | Required for |\n| - | - |\n'
           '| `claude.example` | Login |\n| `new.delivery.example` | Native installer and updates |\n'
           '| `cdn.example` | Shared platform |\n| `login.shared.example` | Native installer |\n',
             'feed':'DOMAIN-SUFFIX,new.delivery.example\nDOMAIN,cdn.example\nDOMAIN,login.shared.example'}
        result=ec.resolve_additions([contract],entries,src,shared_hosts={'login.shared.example'})
        self.assertEqual(result[0]['routes']['claude'],['claude.example','new.delivery.example'])
        self.assertEqual(ec.verify_sources(result,src)['code']['outside-confirmed-scope'],2)
        src['feed']='DOMAIN-SUFFIX,delivery.example'
        result=ec.resolve_additions([deepcopy(contract)],entries,src)
        self.assertNotIn('new.delivery.example',result[0]['routes']['claude'])

    def test_identity_discovers_exact_host_from_a_trusted_issuer_and_excludes_shared_host(self):
        import json
        spec={'format':'openid-discovery','issuer':'https://login.vendor.example',
              'fields':['token_endpoint','userinfo_endpoint'],'roots':['vendor.example'],'exclude':['www.vendor.example']}
        d={'issuer':spec['issuer'],'token_endpoint':'https://new.vendor.example/token',
           'userinfo_endpoint':'https://www.vendor.example/user','documentation':'https://outside.example/'}
        self.assertEqual(extract_rows(spec,json.dumps(d)),{'DOMAIN,new.vendor.example'})
        with self.assertRaises(ValueError): extract_rows(spec,json.dumps(dict(d,issuer='https://other.example')))

    def test_mail_only_accepts_that_providers_server_configuration(self):
        spec={'format':'mail-autoconfig','domain':'gmail.example','roots':['gmail.example']}
        doc='<clientConfig><emailProvider id="example"><domain>gmail.example</domain><incomingServer type="imap"><hostname>imap.gmail.example</hostname></incomingServer></emailProvider><emailProvider><domain>example.org</domain><outgoingServer type="smtp"><hostname>wrong.gmail.example</hostname></outgoingServer></emailProvider></clientConfig>'
        self.assertEqual(extract_rows(spec,doc),{'DOMAIN,imap.gmail.example'})

    def test_small_documented_withdrawal_needs_two_daily_observations(self):
        import calibration
        last=[f'DOMAIN,h{i}.example.org' for i in range(24)]
        feed=last[1:]+['DOMAIN,unproven.other']
        out,obs=calibration.withdrawals(last,feed,{},'v1',0)
        self.assertEqual(out,last)
        out2,_=calibration.withdrawals(last,feed,obs,'v1',3600)
        self.assertEqual(out2,last)
        self.assertEqual(calibration.withdrawals(last,feed,obs,'v1',86400)[0],last[1:])
        self.assertEqual(calibration.withdrawals(last,feed,obs,'changed',86400)[0],last)
        self.assertNotIn('example',str(obs))
        self.assertEqual(calibration.withdrawals(last,feed[10:],obs,'v1',86400)[0],last)
        parent=['DOMAIN-SUFFIX,vendor.example']+last
        children=['DOMAIN,new.vendor.example']+last
        _,state=calibration.withdrawals(parent,children,{},'v1',0)
        self.assertEqual(calibration.withdrawals(parent,children,state,'v1',86400)[0],parent)

    def test_asn_addition_needs_two_feeds_and_cn_allocation_and_preserves_dns_intent(self):
        import calibration
        old=['IP-ASN,100,no-resolve']
        src=old+['IP-ASN,101,no-resolve','IP-ASN,105,no-resolve','IP-ASN,110,no-resolve']
        witness='IP-ASN,101\nIP-ASN,105'
        allocation='apnic|CN|asn|100|4|20200101|allocated\napnic|US|asn|105|1|20200101|assigned'
        out,_=calibration.asn_additions(old,src,witness,allocation)
        self.assertEqual(set(out),set(old+['IP-ASN,101,no-resolve']))

    def test_vendor_network_table_assigns_only_host_column_of_the_named_role(self):
        spec={'format':'destination-table','purpose':'used by vendors to distribute updates',
              'roots':['packages.example'],'ports':'TCP/443'}
        def row(*fields):return '<tr>'+''.join('<td>'+f+'</td>' for f in fields)+'</tr>'
        table='<table>'+row('Destination Host','Ports','Purpose')+row('a.packages.example<br>b.packages.example<br>*.packages.example<br>other.example','TCP/443','Used by vendors to distribute updates. See notes.packages.example.')+row('login.packages.example','TCP/443','Authentication')+row('admin.packages.example','TCP/21','Used by vendors to distribute updates.')+'</table>'
        self.assertEqual(extract_rows(spec,table),{'DOMAIN,a.packages.example','DOMAIN,b.packages.example'})
        with self.assertRaises(ValueError): extract_rows(spec,table.replace('Destination Host','Unknown column'))
