"""AWS service scopes and bundles consume all five documents before producing rules."""
from copy import deepcopy
import unittest

from checks import test_aws_coding_network
from loon_rules.rules import Invalid
from loon_rules.sources import aws_coding, expansion
from loon_rules.generation import dependencies


class AWSCodingExpansion(unittest.TestCase):
    def fixture(self, scope='api'):
        spec, documents = test_aws_coding_network.AWSCodingNetwork().fixture()
        return {**spec, 'method': 'aws-coding-network', 'scope': scope}, documents

    def entries(self):
        spec, documents = self.fixture()
        return {scope: {'id': scope, 'mode': 'compiled', 'sources': list(documents),
                        'expand': {**spec, 'scope': scope}}
                for scope in ('api', 'shared', 'reviews', 'transformations', 'kiro')}, documents

    def collect(self, entries, documents, downloaded=None):
        try:
            return expansion.collect(entries, downloaded or {}, documents.__getitem__)
        except (AttributeError, KeyError, TypeError) as error:
            self.fail('AWS完整资料展开尚未接入：' + str(error))

    def test_scopes_follow_purpose_and_actual_shared_hosts_instead_of_company_ownership(self):
        entries, documents = self.entries()
        rows, report, fetched = self.collect(entries, documents)
        self.assertEqual(rows['api'], ['DOMAIN,codewhisperer.us-east-1.amazonaws.com',
                                      'DOMAIN,q-developer-integration.us-east-1.api.aws'])
        self.assertEqual(rows['shared'], ['DOMAIN,q.eu-central-1.amazonaws.com', 'DOMAIN,q.us-east-1.amazonaws.com'])
        self.assertEqual(rows['reviews'], ['DOMAIN,q-review-one.s3.amazonaws.com'])
        self.assertEqual(rows['transformations'], ['DOMAIN,q-transform-one.s3.amazonaws.com'])
        self.assertEqual(rows['kiro'], ['DOMAIN,runtime.us-east-1.kiro.dev'])
        self.assertEqual(set(fetched), set(documents))
        expansion.verify_report(entries, rows, report)

    def test_five_context_documents_are_fetched_once_for_all_scopes(self):
        entries, documents = self.entries()
        first = next(iter(documents))
        calls = []
        def download(url):
            calls.append(url)
            return documents[url]
        try:
            expansion.collect(entries, {first: documents[first]}, download)
        except (AttributeError, KeyError, TypeError) as error:
            self.fail('完整AWS资料尚未支持共享读取：' + str(error))
        self.assertCountEqual(calls, set(documents) - {first})

    def test_new_api_and_review_bucket_are_discovered_without_prefilled_server_names(self):
        entries, documents = self.entries()
        source = entries['api']['expand']['source']
        documents[source] = documents[source].replace(
            '| `q-developer-integration.us-east-1.api.aws`',
            '| `q-developer-future.eu-central-1.api.aws` | Amazon Q Developer in the IDE, endpoints |\n'
            '| `q-developer-integration.us-east-1.api.aws`').replace(
            '`arn:aws:s3:::q-review-one`', '`arn:aws:s3:::q-review-one` <br /> '
            '`https://new-review-bucket.s3.amazonaws.com/` <br /> `arn:aws:s3:::new-review-bucket`')
        rows, _, _ = self.collect(entries, documents)
        self.assertIn('DOMAIN,q-developer-future.eu-central-1.api.aws', rows['api'])
        self.assertIn('DOMAIN,new-review-bucket.s3.amazonaws.com', rows['reviews'])

    def test_selected_api_cannot_hide_bad_storage_or_unselected_kiro_core_fields(self):
        entries, documents = self.entries()
        for field, before, after in (('source', 'arn:aws:s3:::q-review-one', 'arn:aws:s3:::wrong-bucket'),
                                      ('kiro-source', 'runtime.us-east-1.kiro.dev', '8.8.8.8')):
            spec = entries['api']['expand']
            changed = {**documents, spec[field]: documents[spec[field]].replace(before, after)}
            with self.subTest(field=field), self.assertRaises(Invalid):
                self.collect({'api': entries['api']}, changed)

    def test_bundle_dependencies_read_full_context_and_keep_tooling_and_identity_out_of_api(self):
        spec, documents = self.fixture()
        recipe = {key: value for key, value in spec.items() if key not in ('method', 'scope')}
        recipe.update({'format': 'aws-coding-dependencies', 'protect-from-reject': True})
        entries = {'q-service-all': {'mode': 'view', 'dependency-inputs': [recipe]}}
        try:
            dependencies.validate(entries)
            result = dependencies.read(entries, documents)
        except (AttributeError, KeyError, TypeError, Invalid) as error:
            self.fail('AWS完整服务依赖尚未接入：' + str(error))
        rows = result['q-service-all']['inputs'][0]['rules']
        self.assertIn('DOMAIN,cognito-identity.us-east-1.amazonaws.com', rows)
        self.assertIn('DOMAIN,idetoolkits-hostedfiles.amazonaws.com', rows)
        self.assertIn('DOMAIN,oidc.sa-east-1.amazonaws.com', rows)
        self.assertNotIn('DOMAIN,codewhisperer.us-east-1.amazonaws.com', rows)
        bad = {**documents, spec['source']: documents[spec['source']].replace('arn:aws:s3:::q-review-one', 'arn:aws:s3:::wrong-bucket')}
        with self.assertRaises(Invalid):
            dependencies.read(entries, bad)

    def test_only_declared_business_scopes_can_compile_and_reports_cannot_change_them(self):
        entries, documents = self.entries()
        for change in ({'scope': 'all'}, {'scope': 'authentication'}, {'all-patterns': True}):
            changed = deepcopy(entries)
            changed['api']['expand'].update(change)
            with self.subTest(change=change), self.assertRaises(Invalid):
                expansion.validate({}, changed)
        rows, report, _ = self.collect(entries, documents)
        report['api']['documents'][0]['rows'].append('DOMAIN,unapproved.amazonaws.com')
        with self.assertRaises(Invalid):
            expansion.verify_report(entries, {**rows, 'api': [*rows['api'], 'DOMAIN,unapproved.amazonaws.com']}, report)

    def test_dependency_only_pipeline_reads_secondary_documents_and_retains_the_last_good_files(self):
        from contextlib import redirect_stdout
        from io import StringIO
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from checks import test_service_dependencies
        from checks.source_fixtures import prepare_workspace
        from loon_rules.generation import pipeline

        spec, documents = self.fixture()
        recipe = {key: value for key, value in spec.items() if key not in ('method', 'scope')}
        recipe.update({'format': 'aws-coding-dependencies', 'protect-from-reject': True})
        cfg = test_service_dependencies.ServiceDependencies().config()
        cfg['entries'][1]['dependency-inputs'] = [recipe]
        cfg['view-cases'] = {'api.product.example': ['product-service-all'],
                             'cognito-identity.us-east-1.amazonaws.com': ['product-service-all']}
        cfg['entries'][3]['sources'] = list(documents)
        inputs = {**documents, 'https://lists.example/ads': 'DOMAIN,ads.other.example\n'}
        initial = {'ads': ['DOMAIN,ads.other.example'], 'product': ['DOMAIN-SUFFIX,product.example'],
                   'provider': ['DOMAIN-SUFFIX,shared.example', 'DOMAIN,assets.sharedcdn.example'],
                   'provider-service-all': ['DOMAIN-SUFFIX,shared.example', 'DOMAIN,assets.sharedcdn.example'],
                   'product-service-all': ['DOMAIN-SUFFIX,product.example']}
        with TemporaryDirectory() as temporary, patch.object(pipeline, 'ROOT', prepare_workspace(temporary)), redirect_stdout(StringIO()):
            root = Path(temporary)
            (root / 'rules/loon').mkdir(parents=True)
            entries = pipeline.validate_declarations(cfg)
            (root / 'config/catalog.json').write_text(json.dumps(cfg))
            (root / 'config/endpoint-contracts.json').write_text('[]')
            (root / 'docs/rules.md').write_text(pipeline.render_index(cfg, entries))
            for key, entry in entries.items():
                (root / 'rules/loon' / pipeline.rule_filename(entry)).write_text(
                    pipeline.decorate(entry, initial[key], None, '2026-11-27T00:00:00Z'))
            calls = []
            def download(url):
                calls.append(url)
                return inputs[url]
            with patch.object(pipeline.transport, 'download', side_effect=download):
                try:
                    pipeline.run()
                except KeyError as error:
                    self.fail('仅服务依赖的完整上下文未下载：' + str(error))
                pipeline.run(offline=True)
                self.assertTrue(set(documents) <= set(calls))
                bundle = root / 'rules/loon' / pipeline.rule_filename(entries['product-service-all'])
                self.assertIn('DOMAIN,cognito-identity.us-east-1.amazonaws.com', pipeline.rules.read_rules(bundle.read_text()))
                previous = {file: file.read_bytes() for file in (root / 'rules/loon').glob('*')}
                inputs[spec['kiro-source']] = inputs[spec['kiro-source']].replace('runtime.us-east-1.kiro.dev', '8.8.8.8')
                with self.assertRaises(Invalid):
                    pipeline.run()
                self.assertEqual(previous, {file: file.read_bytes() for file in previous})

    def test_shared_projection_uses_live_expanded_intersection_without_a_fixed_host_list(self):
        from loon_rules.generation.compilation import compile_entry
        source = 'https://community.example/kiro.list'
        entry = {'id': 'q-kiro-shared', 'projection': [{'source': source, 'exact-from-extract': True}]}
        text = 'DOMAIN-SUFFIX,q.us-east-1.amazonaws.com\nDOMAIN-SUFFIX,q.eu-central-1.amazonaws.com\nDOMAIN-SUFFIX,q.ap-southeast-9.amazonaws.com\n'
        try:
            rows = compile_entry(entry, {source: text}, extra_rows=[
                'DOMAIN,q.eu-central-1.amazonaws.com', 'DOMAIN,q.ap-southeast-9.amazonaws.com'])
        except Invalid as error:
            self.fail('动态共用范围尚未用于精确投影：' + str(error))
        self.assertCountEqual(rows, ['DOMAIN,q.ap-southeast-9.amazonaws.com', 'DOMAIN,q.eu-central-1.amazonaws.com'])

    def test_dynamic_projection_declaration_accepts_the_verified_expansion_context(self):
        from checks import test_service_dependencies
        from loon_rules.generation.declarations import validate_declarations
        spec, documents = self.fixture()
        cfg = test_service_dependencies.ServiceDependencies().config()
        product = cfg['entries'][2]
        product['sources'] = list(documents)
        product['expand'] = spec
        product['projection'] = [{'source': spec['source'], 'exact-from-extract': True}]
        try:
            validate_declarations(cfg)
        except Invalid as error:
            self.fail('生成声明未接受完整用途展开字段：' + str(error))

    def test_offline_pipeline_rejects_mismatched_context_and_invalid_region_basis(self):
        import json
        from checks.aws_coding_fixtures import generated_workspace
        with generated_workspace() as (root, spec):
            from loon_rules.generation import pipeline
            state_path = root / 'data/maintenance-state.json'
            good = json.loads(state_path.read_text())
            changes = []
            changed = deepcopy(good)
            changed['service-dependencies']['product-service-all']['inputs'][0]['context-sha256'][spec['kiro-source']] = '0' * 64
            changes.append(changed)
            for region in ({}, {'dns-suffix': 'external.net'}, {'profile-regions': ['ap-southeast-99']},
                           {'sdk-partition': 'aws-cn'}, {'sso-regions': []}):
                changed = deepcopy(good)
                facts = changed['expanded-inputs']['product']['network-facts']
                if not region:
                    facts['regions'] = {}
                else:
                    facts['regions'].update(region)
                changes.append(changed)
            for changed in changes:
                state_path.write_text(json.dumps(changed))
                with self.subTest(state=changed['expanded-inputs']['product']['network-facts']['regions']), self.assertRaises(Invalid):
                    pipeline.run(offline=True)

    def test_dependency_only_offline_path_requires_complete_usable_network_facts(self):
        import json
        from checks.aws_coding_fixtures import generated_workspace
        from loon_rules.generation import pipeline
        with generated_workspace(with_expansion=False) as (root, spec):
            state_path = root / 'data/maintenance-state.json'
            good = json.loads(state_path.read_text())
            changed = deepcopy(good)
            changed['service-dependencies']['product-service-all']['inputs'][0].pop('network-facts', None)
            state_path.write_text(json.dumps(changed))
            with self.assertRaises(Invalid):
                pipeline.run(offline=True)
