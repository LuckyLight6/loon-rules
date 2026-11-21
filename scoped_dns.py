"""Command compatibility entry for the DNS plugin generator."""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))

from loon_rules.plugins.scoped_dns import build,names,main

if __name__ == "__main__":
    raise SystemExit(main())
