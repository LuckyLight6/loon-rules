"""Complete five-source fixtures exercised through the real generation pipeline."""
from contextlib import contextmanager, redirect_stdout
from io import StringIO
import json
from tempfile import TemporaryDirectory
from unittest.mock import patch

from checks import test_aws_coding_network, test_service_dependencies
from checks.source_fixtures import prepare_workspace
from loon_rules.generation import pipeline
from loon_rules.sources import aws_coding


@contextmanager
def generated_workspace(*, with_expansion=True):
    base, documents = test_aws_coding_network.AWSCodingNetwork().fixture()
    spec = {**base, 'method': aws_coding.METHOD, 'scope': 'api'}
    cfg = test_service_dependencies.ServiceDependencies().config()
    recipe = {**base, 'format': aws_coding.DEPENDENCY_FORMAT, 'protect-from-reject': True}
    cfg['entries'][1]['dependency-inputs'] = [recipe]
    cfg['entries'][2]['sources'] = list(documents)
    if with_expansion:
        cfg['entries'][2]['expand'] = spec
    cfg['entries'][3]['sources'] = list(documents)
    cfg['view-cases'] = {'api.product.example': ['product-service-all'],
                         'cognito-identity.us-east-1.amazonaws.com': ['product-service-all']}
    inputs = {**documents, 'https://lists.example/ads': 'DOMAIN,ads.other.example\n'}
    initial = {'ads': ['DOMAIN,ads.other.example'], 'product': ['DOMAIN-SUFFIX,product.example'],
               'provider': ['DOMAIN-SUFFIX,shared.example', 'DOMAIN,assets.sharedcdn.example'],
               'provider-service-all': ['DOMAIN-SUFFIX,shared.example', 'DOMAIN,assets.sharedcdn.example'],
               'product-service-all': ['DOMAIN-SUFFIX,product.example']}
    with TemporaryDirectory(prefix='aws-coding-regression-') as temporary:
        root = prepare_workspace(temporary)
        (root / 'rules/loon').mkdir(parents=True)
        entries = pipeline.validate_declarations(cfg)
        (root / 'config/catalog.json').write_text(json.dumps(cfg))
        (root / 'config/endpoint-contracts.json').write_text('[]')
        (root / 'docs/rules.md').write_text(pipeline.render_index(cfg, entries))
        for key, entry in entries.items():
            (root / 'rules/loon' / pipeline.rule_filename(entry)).write_text(
                pipeline.decorate(entry, initial[key], None, '2026-11-27T00:00:00Z'))
        with patch.object(pipeline, 'ROOT', root), patch.object(pipeline.transport, 'download', side_effect=inputs.__getitem__), redirect_stdout(StringIO()):
            pipeline.run()
            pipeline.run(offline=True)
            yield root, spec
