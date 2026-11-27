"""Every firewall row, variable and service bucket is validated before role selection."""
from copy import deepcopy
import unittest

from loon_rules.rules import Invalid
from loon_rules.sources import aws_coding


class AWSCodingNetwork(unittest.TestCase):
    def fixture(self):
        from checks.test_aws_coding_regions import AWSCodingRegions
        context = AWSCodingRegions()
        region_spec = context.spec()
        region_documents = context.documents()
        source_urls = {
            'profile-source': 'https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/q-admin-setup-subscribe-regions.md',
            'sso-source': 'https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/regions.md',
            'sdk-source': 'https://raw.githubusercontent.com/boto/botocore/develop/botocore/data/endpoints.json'}
        for field, value in source_urls.items():
            region_documents[value] = region_documents.pop(region_spec[field])
            region_spec[field] = value
        region_documents[region_spec['profile-source']] = region_documents[region_spec['profile-source']].replace(
            region_spec['profile-heading'], 'Supported Regions for the Q Developer console and Q Developer profile')
        region_spec['profile-heading'] = 'Supported Regions for the Q Developer console and Q Developer profile'
        region_documents[region_spec['sso-source']] = region_documents[region_spec['sso-source']].replace(
            region_spec['sso-heading'], 'Supported Regions (enabled by default)')
        region_spec['sso-heading'] = 'Supported Regions (enabled by default)'
        spec = {'source': 'https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/firewall.md',
                'kiro-source': 'https://kiro.dev/docs/privacy-and-security/firewalls/',
                'region-context': region_spec}
        body = """# Amazon Q Developer firewall

## General URLs to allowlist

In these URLs, replace {{idc-directory-id-or-alias}}, {{sso-region}} and {{profile-region}} with their documented values.

| URL | Purpose |
| --- | --- |
| `{{idc-directory-id-or-alias}}.awsapps.com` | Authentication |
| `oidc.{{sso-region}}.amazonaws.com` | Authentication |
| `*.sso.{{sso-region}}.amazonaws.com` | Authentication |
| `https://codewhisperer.us-east-1.amazonaws.com` | Amazon Q Developer features |
| `https://q.{{profile-region}}.amazonaws.com` | Amazon Q Developer features |
| `https://idetoolkits-hostedfiles.amazonaws.com/*` | Amazon Q Developer in the IDE, configuration |
| `q-developer-integration.us-east-1.api.aws` | Amazon Q Developer in the IDE, endpoints |
| `https://aws-language-servers.us-east-1.amazonaws.com/*` | Amazon Q Developer in the IDE, language processing |
| `cognito-identity.us-east-1.amazonaws.com` | Amazon Q Developer in the IDE, telemetry |

## Amazon S3 bucket URLs and ARNs to allowlist

These are AWS service-owned S3 buckets for Amazon Q.

| Amazon S3 bucket URL and ARN | Purpose |
| --- | --- |
| Region One: `https://q-review-one.s3.amazonaws.com/` <br /> `arn:aws:s3:::q-review-one` | An Amazon S3 bucket used to upload artifacts for [Amazon Q code reviews](reviews.md) |
| Region One: `https://q-transform-one.s3.amazonaws.com/` <br /> `arn:aws:s3:::q-transform-one` | An Amazon S3 bucket used to upload artifacts for [Amazon Q code transformations](transform.md) |

## Corporate proxy examples

`https://user@private-proxy.example/` is outside the declared network tables.
"""
        editor = ('<h2 id="core-urls">Core URLs</h2><table><tr><th>URL</th><th>Purpose</th></tr>'
                  '<tr><td>q.us-east-1.amazonaws.com</td><td>Kiro service (US East)</td></tr>'
                  '<tr><td>q.eu-central-1.amazonaws.com</td><td>Kiro service (Europe)</td></tr>'
                  '<tr><td>runtime.us-east-1.kiro.dev</td><td>Kiro service (US East)</td></tr></table>')
        documents = {**region_documents, spec['source']: body, spec['kiro-source']: editor}
        return spec, documents

    def read(self, spec, documents):
        try:
            reader = aws_coding.network_records
        except AttributeError:
            self.fail('完整AWS编程网络用途表读取尚未实现')
        return reader(spec, documents)

    def test_full_roles_region_variables_buckets_and_actual_shared_model_intersection(self):
        spec, documents = self.fixture()
        result = self.read(spec, documents)
        self.assertEqual(result['general-purposes']['features'], [
            'DOMAIN,codewhisperer.us-east-1.amazonaws.com',
            'DOMAIN,q.eu-central-1.amazonaws.com', 'DOMAIN,q.us-east-1.amazonaws.com'])
        self.assertEqual(result.get('shared-services'), [
            'DOMAIN,q.eu-central-1.amazonaws.com', 'DOMAIN,q.us-east-1.amazonaws.com'])
        self.assertEqual(result['general-purposes']['authentication'], [
            'DOMAIN,oidc.eu-central-1.amazonaws.com', 'DOMAIN,oidc.sa-east-1.amazonaws.com',
            'DOMAIN,oidc.us-east-1.amazonaws.com', 'DOMAIN-WILDCARD,*.awsapps.com',
            'DOMAIN-WILDCARD,*.sso.eu-central-1.amazonaws.com',
            'DOMAIN-WILDCARD,*.sso.sa-east-1.amazonaws.com', 'DOMAIN-WILDCARD,*.sso.us-east-1.amazonaws.com'])
        self.assertEqual(result['storage-purposes'], {
            'code-reviews': ['DOMAIN,q-review-one.s3.amazonaws.com'],
            'code-transformations': ['DOMAIN,q-transform-one.s3.amazonaws.com']})
        self.assertEqual(result['general-purposes']['ide-endpoints'], ['DOMAIN,q-developer-integration.us-east-1.api.aws'])

    def test_new_literal_endpoint_and_new_bucket_follow_the_purpose_without_prefilled_hosts(self):
        spec, documents = self.fixture()
        documents[spec['source']] = documents[spec['source']].replace(
            '| `q-developer-integration.us-east-1.api.aws`',
            '| `q-developer-integration.eu-central-1.api.aws` | Amazon Q Developer in the IDE, endpoints |\n'
            '| `q-developer-integration.us-east-1.api.aws`')
        documents[spec['source']] = documents[spec['source']].replace(
            '`arn:aws:s3:::q-review-one`', '`arn:aws:s3:::q-review-one` <br /> '
            '`https://q-review-new.s3.amazonaws.com/` <br /> `arn:aws:s3:::q-review-new`')
        result = self.read(spec, documents)
        self.assertEqual(result['general-purposes']['ide-endpoints'], [
            'DOMAIN,q-developer-integration.eu-central-1.api.aws', 'DOMAIN,q-developer-integration.us-east-1.api.aws'])
        self.assertEqual(result['storage-purposes']['code-reviews'], [
            'DOMAIN,q-review-new.s3.amazonaws.com', 'DOMAIN,q-review-one.s3.amazonaws.com'])

    def test_unknown_or_unselected_roles_templates_cloud_roots_and_bad_addresses_stop_the_whole_input(self):
        spec, documents = self.fixture()
        body = documents[spec['source']]
        replacements = [
            ('Authentication |', 'Unclassified identity use |'),
            ('oidc.{{sso-region}}.amazonaws.com', 'oidc.{{unknown-region}}.amazonaws.com'),
            ('oidc.{{sso-region}}.amazonaws.com', 'oidc.sso-region.amazonaws.com'),
            ('cognito-identity.us-east-1.amazonaws.com', '*.amazonaws.com'),
            ('cognito-identity.us-east-1.amazonaws.com', 'https://user@api.example.com/'),
            ('cognito-identity.us-east-1.amazonaws.com', '8.8.8.0/24'),
            ('| URL | Purpose |', '| URL | Purpose | Unknown column |'),
            ('| `cognito-identity.us-east-1.amazonaws.com` | Amazon Q Developer in the IDE, telemetry |',
             '| `cognito-identity.us-east-1.amazonaws.com` | Amazon Q Developer in the IDE, telemetry | hidden.example.com |'),
        ]
        for before, after in replacements:
            with self.subTest(after=after), self.assertRaises(Invalid):
                self.read(spec, {**documents, spec['source']: body.replace(before, after)})

    def test_each_s3_url_and_arn_must_describe_the_same_service_bucket(self):
        spec, documents = self.fixture()
        body = documents[spec['source']]
        for before, after in [('arn:aws:s3:::q-review-one', 'arn:aws:s3:::different-bucket'),
                              ('arn:aws:s3:::q-review-one', 'arn:aws-cn:s3:::q-review-one'),
                              ('`arn:aws:s3:::q-review-one`', ''),
                              ('q-review-one.s3.amazonaws.com', 's3.amazonaws.com'),
                              ('q-review-one.s3.amazonaws.com', 'q-review-one.evil.example.com'),
                              ('Amazon Q code reviews', 'Unclassified storage')]:
            with self.subTest(after=after), self.assertRaises(Invalid):
                self.read(spec, {**documents, spec['source']: body.replace(before, after)})

    def test_network_fields_outside_tables_and_incomplete_or_duplicate_tables_are_not_silently_dropped(self):
        spec, documents = self.fixture()
        body = documents[spec['source']]
        for changed in (body.replace('## Amazon S3 bucket', '`https://hidden.amazonaws.com`\n\n## Amazon S3 bucket'),
                        body.replace('## Amazon S3 bucket', '## General URLs to allowlist\n\n## Amazon S3 bucket'),
                        body.replace('## General URLs to allowlist', '## Unknown section'),
                        body.replace('| `https://q.{{profile-region}}.amazonaws.com` | Amazon Q Developer features |', ''),
                        body.replace('| `https://q.{{profile-region}}.amazonaws.com` | Amazon Q Developer features |',
                                     '| `https://q.{{profile-region}}.amazonaws.com` | Amazon Q Developer features | extra |')):
            with self.subTest(body=changed), self.assertRaises(Invalid):
                self.read(spec, {**documents, spec['source']: changed})

    def test_official_provider_identity_cannot_be_replaced_by_a_lookalike_or_other_namespace(self):
        spec, documents = self.fixture()
        for field, source in (('source', 'https://docs.aws.amazon.com.evil.example/firewall.md'),
                              ('kiro-source', 'https://evil.example/kiro-network')):
            changed = deepcopy(spec)
            changed[field] = source
            with self.subTest(field=field), self.assertRaises(Invalid):
                self.read(changed, {**documents, source: documents[spec[field]]})
        changed = deepcopy(spec)
        original = changed['region-context']['sdk-source']
        changed['region-context']['sdk-source'] = 'https://raw.githubusercontent.com/unverified/botocore/develop/botocore/data/endpoints.json'
        with self.assertRaises(Invalid):
            self.read(changed, {**documents, changed['region-context']['sdk-source']: documents[original]})
        with self.assertRaises(Invalid):
            self.read(spec, {**documents, spec['source']: documents[spec['source']].replace('# Amazon Q Developer firewall', '# Other product firewall')})

    def test_official_empty_anchor_metadata_does_not_change_network_records(self):
        spec, documents = self.fixture()
        body = documents[spec['source']].replace(
            '## General URLs to allowlist', '## General URLs to allowlist\n<a name="firewall-general-urls"></a>').replace(
            '## Amazon S3 bucket URLs and ARNs to allowlist',
            '## Amazon S3 bucket URLs and ARNs to allowlist\n<a name="data-perimeters"></a>')
        try:
            result = self.read(spec, {**documents, spec['source']: body})
        except Invalid as error:
            self.fail('官方空锚点元数据应被保留为结构，不是网络字段：' + str(error))
        self.assertEqual(result.get('shared-services'), [
            'DOMAIN,q.eu-central-1.amazonaws.com', 'DOMAIN,q.us-east-1.amazonaws.com'])

    def test_new_html_blocks_cannot_hide_a_network_field_outside_the_complete_table(self):
        spec, documents = self.fixture()
        body = documents[spec['source']].replace('## Amazon S3 bucket URLs and ARNs to allowlist',
            '<div>https://hidden.amazonaws.com</div>\n\n## Amazon S3 bucket URLs and ARNs to allowlist')
        with self.assertRaises(Invalid):
            self.read(spec, {**documents, spec['source']: body})

    def test_profile_and_sso_consumers_cannot_swap_their_official_purpose_lists(self):
        spec, documents = self.fixture()
        spec['region-context']['profile-source'] = spec['region-context']['sso-source']
        spec['region-context']['profile-heading'] = spec['region-context']['sso-heading']
        with self.assertRaises(Invalid):
            self.read(spec, documents)

    def test_region_templates_cannot_claim_an_external_dns_namespace(self):
        spec, documents = self.fixture()
        body = documents[spec['source']].replace('q.{{profile-region}}.amazonaws.com',
                                                 'q.{{profile-region}}.third-party.net')
        with self.assertRaises(Invalid):
            self.read(spec, {**documents, spec['source']: body})

    def test_complete_kiro_core_intersection_does_not_depend_on_a_purpose_prefix(self):
        spec, documents = self.fixture()
        documents[spec['kiro-source']] = documents[spec['kiro-source']].replace(
            'Kiro service (Europe)', 'Legacy code assistance')
        result = self.read(spec, documents)
        self.assertEqual(result.get('shared-services'), [
            'DOMAIN,q.eu-central-1.amazonaws.com', 'DOMAIN,q.us-east-1.amazonaws.com'])

    def test_every_kiro_core_table_is_validated_before_selecting_shared_services(self):
        spec, documents = self.fixture()
        original = documents[spec['kiro-source']]
        good = ('<table><tr><th>URL</th><th>Purpose</th></tr>'
                '<tr><td>new.kiro.dev</td><td>New code capability</td></tr></table>')
        result = self.read(spec, {**documents, spec['kiro-source']: original + good})
        self.assertIn('DOMAIN,new.kiro.dev', result.get('kiro-core-services', []))
        for table in (good.replace('new.kiro.dev', '8.8.8.8'),
                      good.replace('<th>Purpose</th>', '<th>Unclassified</th>'),
                      good.replace('<td>New code capability</td>', ''),
                      good.replace('<td>New code capability</td>', '<td></td>')):
            with self.subTest(table=table), self.assertRaises(Invalid):
                self.read(spec, {**documents, spec['kiro-source']: original + table})

    def test_business_api_roles_cannot_claim_external_literal_hosts_by_a_matching_label(self):
        spec, documents = self.fixture()
        body = documents[spec['source']]
        for before, after in [('codewhisperer.us-east-1.amazonaws.com', 'api.third-party.net'),
                              ('q-developer-integration.us-east-1.api.aws', 'q-developer-integration.third-party.net')]:
            with self.subTest(after=after), self.assertRaises(Invalid):
                self.read(spec, {**documents, spec['source']: body.replace(before, after)})

    def test_s3_purpose_requires_an_unambiguous_positive_service_usage_statement(self):
        spec, documents = self.fixture()
        body = documents[spec['source']]
        for statement in ('An Amazon S3 bucket not used to upload artifacts for',
                          'An external bucket mentioning',
                          'A retired bucket formerly used for'):
            changed = body.replace('An Amazon S3 bucket used to upload artifacts for', statement)
            with self.subTest(statement=statement), self.assertRaises(Invalid):
                self.read(spec, {**documents, spec['source']: changed})

    def test_markdown_without_boundary_pipes_is_complete_and_extra_cells_are_rejected(self):
        spec, documents = self.fixture()
        original = documents[spec['source']]
        plain = '\n'.join(line.strip().strip('|').strip() if line.lstrip().startswith('|') else line
                          for line in original.splitlines())
        result = self.read(spec, {**documents, spec['source']: plain})
        self.assertEqual(result['general-records'], 9)
        row = next(line for line in plain.splitlines() if 'cognito-identity.us-east-1.amazonaws.com' in line)
        for line in (row + ' | hidden.other.net', row + ' | hidden.other.net |'):
            with self.subTest(line=line), self.assertRaises(Invalid):
                self.read(spec, {**documents, spec['source']: plain.replace(row, line)})

    def test_unhandled_region_html_lists_fences_and_code_blocks_stop_the_source(self):
        spec, documents = self.fixture()
        source = spec['region-context']['profile-source']
        for extra in ('<ul><li>South America (São Paulo)</li></ul>',
                      '<div>South America (São Paulo)</div>',
                      '```\n+ South America (São Paulo)\n```',
                      '    South America (São Paulo)'):
            body = documents[source].replace('### Other uses', extra + '\n\n### Other uses')
            with self.subTest(extra=extra), self.assertRaises(Invalid):
                self.read(spec, {**documents, source: body})

    def test_an_ide_business_api_is_shared_when_both_official_core_tables_require_it(self):
        spec, documents = self.fixture()
        body = documents[spec['kiro-source']].replace('</table>',
            '<tr><td>q-developer-integration.us-east-1.api.aws</td><td>IDE integration</td></tr></table>')
        result = self.read(spec, {**documents, spec['kiro-source']: body})
        self.assertIn('DOMAIN,q-developer-integration.us-east-1.api.aws', result['shared-services'])
        scoped = aws_coding.scoped_rows(spec, result)
        self.assertNotIn('DOMAIN,q-developer-integration.us-east-1.api.aws', scoped['api'])
