"""Check every selection through its relevant choices, against a small exhaustive oracle."""
import random
import unittest

from loon_rules.rules import Invalid
from loon_rules.matching import RuleIndex
from loon_rules.generation import pipeline
from loon_rules.generation.ordering import subscription_order, view_replacements, view_selections


def exhaustive(config, entries, data):
    index=RuleIndex(data,subscription_order(config,entries));bits=index.bits
    base=set(config['detailed']+config['general']);count=0
    for views in view_selections(config,entries):
        replacements=view_replacements(config,entries,views)
        selected=base-set(replacements)|set(replacements.values())
        mask=sum(bits[key] for key in selected);seen=set()
        for key in selected:
            for row in set(index.identities[key]):
                if row in seen:raise Invalid('duplicate')
                seen.add(row)
        for host,wanted in config['critical'].items():
            matching=index.domain_bits(host)&mask
            first=matching&-matching
            expected=sum(bits[replacements.get(key,key)] for key in set(wanted))
            if (first and not first&expected) or (not first and expected):raise Invalid('route')
        count+=1
    return count


class ChoiceProjection(unittest.TestCase):
    def fixture(self, count=3):
        fine=[f'p{i}' for i in range(count)];views=[f'v{i}-all' for i in range(count)]
        order=views+fine
        config={'detailed':fine,'general':[],'views':views,
                'routing-bands':[{'ids':order}],
                'critical':{f'{key}.example':[key] for key in fine}}
        entries={key:{'priority':i} for i,key in enumerate(order)}
        data={key:['DOMAIN,'+key+'.example'] for key in fine}
        for view,key in zip(views,fine):
            entries[view]['members']=[key];data[view]=list(data[key])
        return config,entries,data

    def test_independent_bundles_do_not_require_enumerating_millions_of_profiles(self):
        config,entries,data=self.fixture(28)
        self.assertEqual(pipeline.verify_combinations(config,entries,data),2**28)

    def test_overlapping_bundles_have_exactly_the_legal_selections(self):
        config,entries,data=self.fixture()
        entries['v0-all']['members']=['p0','p1']
        data['v0-all']=data['p0']+data['p1']
        entries['v1-all']['members']=['p1','p2']
        data['v1-all']=data['p1']+data['p2']
        self.assertEqual(pipeline.verify_combinations(config,entries,data),exhaustive(config,entries,data))
        selections=list(view_selections(config,entries,maximal=True))
        self.assertEqual(set(selections),{('v0-all','v2-all'),('v1-all',)})

    def test_a_bundle_that_drops_a_member_is_checked_even_when_it_does_not_match(self):
        config,entries,data=self.fixture()
        data['v1-all']=[]
        with self.assertRaises(Invalid):pipeline.verify_combinations(config,entries,data)

    def test_shared_dependency_guards_apply_to_the_same_specialties_for_fine_and_combined_rules(self):
        config,entries,data=self.fixture(1)
        config['critical']={'api.github.com':['p0']};config['shared-negatives']=['api.github.com']
        for entry in entries.values():entry['section']='development'
        data={'p0':['DOMAIN,api.github.com'],'v0-all':['DOMAIN,api.github.com']}
        pipeline.verify_cases(config,entries,data,False)
        for entry in entries.values():entry['section']='ai'
        with self.assertRaisesRegex(Invalid,'共享端点'):
            pipeline.verify_cases(config,entries,data,False)

    def test_complete_scope_order_checks_unknown_children_and_excludes_mutually_exclusive_pairs(self):
        from loon_rules.generation.validation import verify_selection_order
        config,entries,data=self.fixture(2)
        verify_selection_order(config,entries,data,RuleIndex(data,subscription_order(config,entries)))
        data['p0']=['DOMAIN-SUFFIX,shared.example']
        data['v0-all']=list(data['p0'])
        data['p1']=['DOMAIN-WILDCARD,p??.shared.example']
        data['v1-all']=list(data['p1'])
        with self.assertRaisesRegex(Invalid,'提前覆盖'):
            verify_selection_order(config,entries,data,RuleIndex(data,subscription_order(config,entries)))

    def test_projection_agrees_with_exhaustive_routing_and_duplicates_on_small_candidates(self):
        randomizer=random.Random(23)
        for trial in range(50):
            config,entries,data=self.fixture(4)
            for view in config['views']:
                members=randomizer.sample(config['detailed'],randomizer.randint(1,3))
                entries[view]['members']=members
                data[view]=[row for member in members for row in data[member]]
            if trial%3==0:data['v0-all']+=data['p3']
            if trial%5==0:data['v2-all']=[]
            def result(check):
                try:return check(config,entries,data)
                except Invalid:return 'invalid'
            with self.subTest(trial=trial):
                self.assertEqual(result(pipeline.verify_combinations),result(exhaustive))
