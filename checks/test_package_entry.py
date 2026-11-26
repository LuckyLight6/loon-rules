from pathlib import Path
import os
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import patch


ROOT=Path(__file__).resolve().parents[1]


class PackageEntry(unittest.TestCase):
    def test_invalid_input_is_reported_without_a_traceback(self):
        from loon_rules import cli,rules
        from loon_rules.generation import pipeline
        errors=StringIO()
        with patch('sys.argv',['loon_rules','--verify-files']),redirect_stderr(errors),\
                patch.object(pipeline,'run',side_effect=rules.Invalid('范围无效')):
            self.assertEqual(cli.main(),2)
        self.assertEqual(errors.getvalue(),'保留上一版本：范围无效\n')

    def test_package_command_checks_the_actual_repository(self):
        result=subprocess.run([sys.executable,'-B','-m','loon_rules','--verify-files'],
                              cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn(str(len(list((ROOT/'rules' / 'loon').glob('*.lsr'))))+' 份',result.stdout)

    def test_original_script_entry_still_checks_the_repository(self):
        with TemporaryDirectory() as outside:
            result=subprocess.run([sys.executable,'-B',str(ROOT/'maintain.py'),'--verify-files'],
                                  cwd=outside,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('种细分与合集组合通过',result.stdout)

    def installed_command(self, cwd, *args):
        # Ordinary installations place code outside the checkout. Exercise that
        # layout rather than letting the editable source path hide the error.
        with TemporaryDirectory() as temporary:
            site=Path(temporary)/'site-packages'
            shutil.copytree(ROOT/'src/loon_rules',site/'loon_rules',
                            ignore=shutil.ignore_patterns('__pycache__'))
            env=dict(os.environ,PYTHONPATH=str(site))
            return subprocess.run([sys.executable,'-B','-m','loon_rules',*args],
                                  cwd=cwd if cwd is not None else temporary,
                                  env=env,capture_output=True,text=True)

    def test_installed_command_finds_checkout_from_a_subdirectory(self):
        result=self.installed_command(ROOT/'docs','--verify-files')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('种细分与合集组合通过',result.stdout)

    def test_installed_help_does_not_require_a_checkout(self):
        result=self.installed_command(None,'--help')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('--verify-files',result.stdout)

    def test_installed_command_explains_missing_checkout(self):
        result=self.installed_command(None,'--verify-files')
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('请先进入规则仓库目录',result.stderr)
        self.assertNotIn('Traceback',result.stderr)
