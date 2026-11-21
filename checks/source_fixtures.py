"""Give synthetic .example hosts a declared public suffix without making network requests."""
import unittest
from unittest.mock import patch

from loon_rules import domains as domain_scope


class PublicSourceExamples(unittest.TestCase):
    def setUp(self):
        super().setUp()
        source='''// ===BEGIN ICANN DOMAINS===
com
net
org
example
uk
co.uk
io
ai
sh
run
// ===END ICANN DOMAINS===
// ===BEGIN PRIVATE DOMAINS===
github.io
zendesk.com
// ===END PRIVATE DOMAINS===
'''
        change=patch.object(domain_scope,'_current',domain_scope.Suffixes(source))
        change.start();self.addCleanup(change.stop)


def prepare_workspace(path):
    from pathlib import Path
    root=Path(path)
    for name in ("config","docs","data","build"):(root/name).mkdir(exist_ok=True)
    return root


def repository_rows(root, config):
    import json
    from loon_rules.rules import read_rules
    from loon_rules.catalog import rule_filename
    rows={entry['id']:read_rules((root/'rules'/rule_filename(entry)).read_text())
          for entry in config['entries']}
    rows.update(json.loads((root/'data/maintenance-state.json').read_text()).get('component-rules',{}))
    return rows
