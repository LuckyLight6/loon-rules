"""Repository paths shared by command entry points and data readers."""
from pathlib import Path


def repository_at(path):
    return all((path/name).is_file() for name in (
        'config/catalog.json','config/scope-policy.json',
        'data/public-suffix-list.dat',
    ))


def find_root():
    checkout=Path(__file__).resolve().parents[2]
    if repository_at(checkout):
        return checkout
    current=Path.cwd().resolve()
    for candidate in (current,*current.parents):
        if repository_at(candidate):
            return candidate
    raise FileNotFoundError('找不到规则仓库，请先进入规则仓库目录再运行 loon-rules')


ROOT = find_root()
