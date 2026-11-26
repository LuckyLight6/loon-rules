import json
import unittest

from loon_rules.generation import pipeline as lib
from loon_rules.rules import Invalid


class AuditConventions(unittest.TestCase):
    def test_optional_extended_ads_precede_product_parents_in_the_actual_catalog(self):
        config = json.loads((lib.ROOT / 'config/catalog.json').read_text())
        entries = lib.validate_declarations(config)
        order = lib.subscription_order(config, entries)
        self.assertLess(order.index('general-ad-and-tracking'), order.index('extended-ad-and-tracking'))
        for product in order:
            if entries[product]['section'] not in ('network', 'privacy'):
                self.assertLess(order.index('extended-ad-and-tracking'), order.index(product))

    def test_published_maintenance_labels_refer_to_the_current_catalog_numbers(self):
        config=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entries=lib.validate_declarations(config)
        by_number={entry['priority']:entry for entry in entries.values() if 'priority' in entry}
        methods=json.loads((lib.ROOT/'data/maintenance-state.json').read_text())['maintenance']
        self.assertCountEqual([number for numbers in methods.values() for number in numbers],by_number)
        for method,numbers in methods.items():
            for number in numbers:
                self.assertEqual(lib.maintenance_method(by_number[number]),method)

    def test_conservative_ads_protect_named_sites_without_whitelisting_ad_subdomains(self):
        cfg={'routing-bands':[{'ids':['ads-extra','sites-extra']}],
             'detailed':[],'general':['sites-extra'],'optional':['ads-extra']}
        entries={'ads-extra':{'domain-remainder':True,'policy-hint':'reject',
                              'protect-site-scopes':True},
                 'sites-extra':{'fallback':True,'policy-hint':'global'}}
        original={'ads-extra':['DOMAIN-SUFFIX,shared.test','DOMAIN-SUFFIX,wide.test',
                               'DOMAIN,tracker.child.test','DOMAIN-SUFFIX,ads-only.test'],
                  'sites-extra':['DOMAIN-SUFFIX,shared.test','DOMAIN,login.wide.test',
                                 'DOMAIN-SUFFIX,child.test']}
        data={key:list(rows) for key,rows in original.items()}
        assigned=lib.apply_domain_ownership(cfg,entries,data)
        self.assertEqual(data['ads-extra'],['DOMAIN,tracker.child.test','DOMAIN-SUFFIX,ads-only.test'])
        self.assertEqual(set(assigned['ads-extra']),set(original['ads-extra'][:2]))
        for host in ('www.shared.test','login.wide.test'):
            self.assertEqual(lib.ordered_route(host,['ads-extra','sites-extra'],data),'sites-extra')
        self.assertEqual(lib.ordered_route('tracker.child.test',['ads-extra','sites-extra'],data),'ads-extra')
        data['ads-extra']=lib.restore_assigned_rules(data['ads-extra'],assigned['ads-extra'])
        self.assertEqual(lib.apply_domain_ownership(cfg,entries,data),assigned)

    def test_maintenance_inventory_does_not_call_fixed_or_baseline_rows_discovered(self):
        entries={
            'fixed':{'mode':'compiled','priority':11,'include':['DOMAIN,a.example'],
                     'literal_ips':['IP-CIDR,169.254.0.0/16'],'dns_required':['IP-CIDR,10.0.0.0/8']},
            'mixed':{'mode':'compiled','priority':12,'include':['DOMAIN,b.example'],
                     'extract':[{'source':'doc'}]},
            'scoped':{'mode':'compiled','priority':13,'projection':[{'source':'feed','roots':['c.example']}]},
            'baseline':{'mode':'managed','priority':14},
            'combined-all':{'mode':'view','priority':15,'members':['fixed','mixed']}}
        contracts=[{'routes':{'fixed':['a.example'],'mixed':['b.example']}}]
        report=lib.maintenance_audit(entries,contracts)
        self.assertEqual(report['fixed-declarations'],{'fixed':3,'mixed':1})
        self.assertEqual(report['fixed-only'],['fixed'])
        self.assertEqual(report['baseline-managed'],['baseline'])
        self.assertEqual(report['official-checks'],{'fixed':1,'mixed':1})
        self.assertEqual(report['source-scoped'],['mixed','scoped'])

    def test_exact_name_selectors_are_counted_separately_from_generated_rules(self):
        entry={'mode':'compiled','priority':1,'extract':[{'exact':['api.example.com'],
               'select':[{'exact':['status.example.com'],'roots':['example.com']}]}],
               'projection':[{'exact':['cdn.example.com'],'roots':['example.com']}]}
        audit=lib.maintenance_audit({'service':entry},[])
        self.assertEqual(audit['exact-selectors'],{'service':3})
        self.assertEqual(audit['fixed-declarations'],{})

    def test_aggregate_and_alternative_names_express_their_role(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entries=lib.validate_declarations(cfg)
        for key,entry in entries.items():
            with self.subTest(rule=key):
                self.assertEqual(key.endswith('-all'),entry['mode']=='view')
        for key in cfg['alternatives']:
            with self.subTest(alternative=key):
                self.assertTrue(key.endswith(('-alt','-compat')))

    def test_published_networks_cannot_have_host_bits(self):
        for row in ('IP-CIDR,13.251.24.157/24,no-resolve',
                    'IP-CIDR,108.168.174.0/16,no-resolve',
                    'IP-CIDR6,2001:db8::1/64,no-resolve'):
            with self.subTest(row=row),self.assertRaises(Invalid):
                lib.lint_content('compat',[row])

    def test_bad_upstream_network_is_excluded_and_reported(self):
        valid='IP-CIDR,203.0.113.0/24,no-resolve'
        entry={'id':'source-compat','mode':'managed','sources':['source'],
               'kinds':['IP-CIDR'],'flags':['no-resolve'],'ip-match':'target-ip'}
        output,review=lib.refresh_reviewed_feed(entry,[valid],
            {'source':valid+'\nIP-CIDR,198.51.100.42/24,no-resolve'})
        self.assertEqual(output,[valid])
        self.assertEqual(review['unaligned-prefixes'],1)
        self.assertEqual(review['state'],'current')

    def test_regional_product_hosts_need_approved_brand_domains(self):
        entry={'id':'scholar','projection':[{'source':'product','roots':['scholar.google.com'],
                'parent-domains-source':'official','brand-label':'google','prefix-label':'scholar'}]}
        inputs={'product':'DOMAIN,scholar.google.com\nDOMAIN,scholar.google.co.jp\nDOMAIN,scholar.evil.test\nDOMAIN,accounts.google.co.jp',
                'official':'.google.com\n.google.co.jp\n'}
        self.assertEqual(set(lib.compile_entry(entry,inputs)),
                         {'DOMAIN,scholar.google.com','DOMAIN,scholar.google.co.jp'})
        with self.assertRaises(Invalid):
            lib.compile_entry(entry,{**inputs,'official':'.google.com\n.evil.test\n'})

    def test_region_links_do_not_claim_shared_hosts_or_other_regions(self):
        recipe={'format':'brand-region-links','brand-label':'nintendo','excluded-tlds':['cn']}
        doc=''.join('<a href="'+url+'">region</a>' for url in [
            'https://www.nintendo.com/','https://www.nintendo.dk/',
            'http://www.nintendo.co.za/','https://fonts.googleapis.com/',
            'https://www.nintendoswitch.com.cn/','https://www.nintendo.com.cn/',
            'https://www.nintendo.evil.test/','https://www.nintendo.dk@evil.test/'])
        self.assertEqual(lib.extract_rows(recipe,doc),{'DOMAIN-SUFFIX,nintendo.com',
                         'DOMAIN-SUFFIX,nintendo.dk','DOMAIN-SUFFIX,nintendo.co.za'})

    def test_regular_service_tables_do_not_capture_entire_clients(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text())
        entries=lib.validate_declarations(cfg)
        permitted={'DOMAIN','DOMAIN-SUFFIX','DOMAIN-WILDCARD','IP-CIDR','IP-CIDR6','IP-ASN'}
        for key in cfg['detailed']+cfg['general']:
            if entries[key].get('fallback'):continue
            rows=lib.rules.read_rules((lib.ROOT/'rules' / 'loon'/lib.rule_filename(entries[key])).read_text())
            with self.subTest(service=key):
                self.assertFalse({r.split(',')[0] for r in rows}-permitted)

    def test_all_aggregate_combinations_use_the_same_business_owners(self):
        cfg={'routing-bands':[{'ids':['a','b','b-all','a-all']}],
             'detailed':['a','b'],'general':[],'views':['a-all','b-all'],
             'critical':{'a.test':['a'],'b.test':['b']},'ip-cases':[]}
        entries={'a':{},'b':{},'a-all':{'members':['a']},'b-all':{'members':['b']}}
        rows={'a':['DOMAIN,a.test'],'b':['DOMAIN,b.test'],
              'a-all':['DOMAIN,a.test'],'b-all':['DOMAIN,b.test']}
        self.assertEqual(lib.verify_combinations(cfg,entries,rows),4)
        with self.assertRaises(Invalid):
            lib.verify_combinations(cfg,entries,{**rows,'b-all':['DOMAIN,a.test','DOMAIN,b.test']})

    def test_equivalent_targets_still_keep_different_expected_owners(self):
        cfg={'detailed':['a','b'],'general':[],'views':[],
             'critical':{'one.example':['a'],'two.example':['b']}}
        entries={'a':{'priority':10},'b':{'priority':20}}
        rows={'a':['DOMAIN-SUFFIX,example'],'b':[]}
        with self.assertRaisesRegex(Invalid,'two.example'):
            lib.verify_combinations(cfg,entries,rows)
        cfg['critical']={'one.example':['a'],'two.example':['a'],'absent.test':['b']}
        with self.assertRaisesRegex(Invalid,'absent.test'):
            lib.verify_combinations(cfg,entries,rows)

    def test_literal_address_and_no_expected_owner_remain_distinct_cases(self):
        cfg={'detailed':['dns'],'general':[],'views':['dns-all'],'critical':{},
             'ip-cases':[{'target':'1.1.1.1','literal':True,'rule':'dns'},
                         {'target':'1.1.1.1','literal':False,'rule':None}]}
        entries={'dns':{'priority':20},'dns-all':{'priority':10,'members':['dns']}}
        rows={'dns':['IP-CIDR,1.1.1.1/32,no-resolve'],
              'dns-all':['IP-CIDR,1.1.1.1/32,no-resolve']}
        self.assertEqual(lib.verify_combinations(cfg,entries,rows),2)
        cfg['ip-cases'][1]['rule']='dns'
        with self.assertRaises(Invalid):
            lib.verify_combinations(cfg,entries,rows)

    def test_regular_selection_has_no_repeated_rules(self):
        cfg=json.loads((lib.ROOT/'config/catalog.json').read_text());entries=lib.validate_declarations(cfg)
        owners={}
        for key in lib.route_order(cfg,entries):
            rows=lib.rules.read_rules((lib.ROOT/'rules' / 'loon'/lib.rule_filename(entries[key])).read_text())
            for row in rows:
                self.assertFalse(row in owners,(row,key,owners.get(row)))
                owners[row]=key

    def test_domain_remainders_keep_broader_parents_and_record_ownership(self):
        cfg={'routing-bands':[{'ids':['service','extra']}],
             'detailed':['service'],'general':['extra'],'views':[],'optional':[]}
        entries={'service':{},'extra':{'domain-remainder':True}}
        original={'service':['DOMAIN,api.parent.test','DOMAIN-SUFFIX,owned.test','DOMAIN,exact.test'],
                  'extra':['DOMAIN,exact.test','DOMAIN-SUFFIX,owned.test',
                           'DOMAIN-SUFFIX,parent.test','DOMAIN,other.test']}
        data={k:list(v) for k,v in original.items()}
        assigned=lib.apply_domain_ownership(cfg,entries,data)
        self.assertEqual(data['extra'],['DOMAIN-SUFFIX,parent.test','DOMAIN,other.test'])
        self.assertEqual(assigned,{'extra':{'DOMAIN,exact.test':'service',
                                          'DOMAIN-SUFFIX,owned.test':'service'}})
        restored=lib.restore_assigned_rules(data['extra'],assigned['extra'])
        self.assertEqual(set(restored),set(original['extra']))

    def test_approved_scope_returns_to_remainder_when_a_product_is_removed(self):
        extra=['DOMAIN,other.test'];assigned={'DOMAIN-SUFFIX,owned.test':'removed-product'}
        baseline=lib.restore_assigned_rules(extra,assigned)
        entry={'id':'extra','mode':'managed','sources':['feed'],
               'kinds':['DOMAIN','DOMAIN-SUFFIX'],'flags':[]}
        effective,state=lib.refresh_reviewed_feed(entry,baseline,{'feed':'\n'.join(baseline)})
        self.assertEqual(set(effective),set(baseline))
        self.assertEqual(state['state'],'current')
        cfg={'routing-bands':[{'ids':['extra']}],'detailed':[],
             'general':['extra'],'optional':[],'views':[]}
        data={'extra':effective}
        self.assertEqual(lib.apply_domain_ownership(cfg,{'extra':{'domain-remainder':True}},data),{})
        self.assertIn('DOMAIN-SUFFIX,owned.test',data['extra'])

    def test_optional_ad_rule_can_override_a_late_site_fallback(self):
        cfg={'routing-bands':[{'ids':['service','ads-extra','sites-extra']}],
             'detailed':['service'],'general':['sites-extra'],'views':[],
             'optional':['ads-extra'],'critical':{'api.service.test':['service']}}
        entries={'service':{},'ads-extra':{'domain-remainder':True,'policy-hint':'reject'},
                 'sites-extra':{'fallback':True,'policy-hint':'global'}}
        data={'service':['DOMAIN,api.service.test'],
              'ads-extra':['DOMAIN-SUFFIX,tracking.test'],
              'sites-extra':['DOMAIN-SUFFIX,tracking.test']}
        self.assertEqual(lib.ordered_route('tracking.test',['service','sites-extra'],data),'sites-extra')
        self.assertEqual(lib.ordered_route('tracking.test',['service','ads-extra','sites-extra'],data),'ads-extra')
        self.assertEqual(lib.verify_combinations(cfg,entries,data),2)
        with self.assertRaises(Invalid):
            lib.verify_combinations(cfg,{**entries,'sites-extra':{'fallback':False}},data)

    def test_audit_reports_routine_conflicts_and_optional_overrides_separately(self):
        cfg={'routing-bands':[{'ids':['service','ads','sites']}],
             'detailed':['service'],'general':['sites'],'optional':['ads']}
        entries={'service':{},'ads':{},'sites':{}}
        data={'service':['DOMAIN,api.test'],
              'ads':['DOMAIN,tracking.test'],
              'sites':['DOMAIN,api.test','DOMAIN,tracking.test']}
        report=lib.subscription_audit(cfg,entries,data)
        self.assertEqual(report,{'routine-tables':2,'duplicate-rules':1,
                               'shadowed-domain-rules':1,
                               'optional-overlaps':{'ads':{'sites':1}}})
        self.assertNotIn('api.test',json.dumps(report))
