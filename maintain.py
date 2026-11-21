"""Command compatibility entry; implementation lives in loon_rules."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))

from loon_rules.rules import *
from loon_rules.sources.transport import download,source_url
from loon_rules.sources.formats.html import HostTables,AppleTables,HIDDEN_HTML
from loon_rules.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
