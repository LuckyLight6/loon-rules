import copy
import unittest

from loon_rules.rules import Invalid


class SourcePolicyChecks(unittest.TestCase):
    def fixture(self):
        return ({'source-alias-policies': {'vendor': {
            'parents': {'example.com': ['example.com.cdn.net']},
            'label-modifiers': ['cdn', 'lb']}}}, {
                'product': {'mode': 'managed', 'sources': ['feed', 'doc'],
                    'discovery': {'inputs': [
                        {'source': 'feed', 'family': 'community'},
                        {'source': 'doc', 'family': 'vendor', 'authority': True,
                         'recipe': {'format': 'python-sdk-endpoints', 'fields': ['base_url']}}]}}})

    def test_valid_product_discovery_has_explicit_evidence_and_lineage(self):
        from loon_rules.sources.policy import validate
        validate(*self.fixture())

    def test_reference_documents_are_not_parsed_as_community_rule_feeds(self):
        from loon_rules.generation.pipeline import refresh_reviewed_feed
        entry={'id':'service','mode':'managed','sources':['feed','sdk'],
               'kinds':['DOMAIN'],'flags':[],'discovery':{'inputs':[
                   {'source':'feed','family':'community'},
                   {'source':'sdk','family':'vendor','authority':True,
                    'recipe':{'format':'python-sdk-endpoints','fields':['base_url']}}]}}
        rows=['DOMAIN,api.example.com']
        output,stats=refresh_reviewed_feed(entry,rows,{'feed':rows[0],'sdk':'SDK Python code, not Loon syntax'})
        self.assertEqual(stats['state'],'current')
        self.assertEqual(output,rows)

    def test_required_service_aliases_are_protected_without_whitelisting_the_cdn(self):
        from loon_rules.generation.pipeline import functional_hostnames
        entry={'aliases':{'protect-from-reject':True}}
        result=functional_hostnames({'download':entry},{},
                   aliases={'download':['DOMAIN,download.g.images.example.com']})
        self.assertEqual(result,{'download.g.images.example.com'})

    def test_discovery_cannot_treat_one_feed_as_two_independent_families(self):
        from loon_rules.sources.policy import validate
        cfg, entries = self.fixture()
        entries['product']['discovery']['inputs'].append({'source': 'feed', 'family': 'mirror'})
        with self.assertRaises(Invalid):
            validate(cfg, entries)

    def test_unscoped_authority_and_one_vote_threshold_are_rejected(self):
        from loon_rules.sources.policy import validate
        for change in ('recipe', 'threshold', 'undeclared', 'blank-family', 'fallback'):
            cfg, entries = self.fixture()
            entry = entries['product']
            spec = entry['discovery']
            if change == 'recipe':
                spec['inputs'][1].pop('recipe')
            elif change == 'threshold':
                spec['minimum-families'] = 1
            elif change == 'undeclared':
                spec['inputs'][1]['source'] = 'unlisted'
            elif change == 'blank-family':
                spec['inputs'][1]['family'] = ''
            elif change == 'fallback':
                entry['fallback'] = True
            with self.subTest(change=change), self.assertRaises(Invalid):
                validate(cfg, entries)

    def test_alias_policy_must_exist_and_keep_all_sources_declared(self):
        from loon_rules.sources.policy import validate
        cfg, entries = self.fixture()
        entry = entries['product']
        entry['mode'] = 'compiled'
        entry['aliases'] = {'policy': 'vendor', 'sources': ['feed'], 'resolve-cname': True}
        validate(cfg, entries)
        for edit in ({'policy': 'unknown'}, {'sources': ['unlisted']}, {'resolve-cname': 'yes'}):
            candidate = copy.deepcopy(entries)
            candidate['product']['aliases'].update(edit)
            with self.subTest(edit=edit), self.assertRaises(Invalid):
                validate(cfg, candidate)

    def test_wildcard_alias_parents_cannot_broaden_the_service_namespace(self):
        from loon_rules.sources.policy import validate
        cfg, entries = self.fixture()
        cfg['source-alias-policies']['vendor']['parents']['example.com'] = ['*.cdn.net']
        with self.assertRaises(Invalid):
            validate(cfg, entries)

    def test_cname_tenants_require_a_known_service_parent_and_a_private_suffix(self):
        from loon_rules.sources.policy import validate
        cfg,entries=self.fixture();policy=cfg['source-alias-policies']['vendor']
        policy['cname-tenants']={'example.com':['trafficmanager.net']}
        validate(cfg,entries)
        for tenants in ({'other.example.net':['trafficmanager.net']},{'example.com':['com']},
                        {'example.com':['microsoft.com']},{'example.com':['*.trafficmanager.net']}):
            policy['cname-tenants']=tenants
            with self.subTest(tenants=tenants),self.assertRaises(Invalid):validate(cfg,entries)
