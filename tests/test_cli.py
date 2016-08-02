
# python 2 support via python-future
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import str

import glob
import os
import shlex

import click.testing
import pytest

from mariobros import cli

TOUCH_FILE = r"""touched-11-22.file: touched-11.file touched-22.file
    touch ${TARGET}

[touch_single]
touched-([^-.]+).file:
    touch ${TARGET}"""


def test_mariobros(tmpdir):
    mario_folder = tmpdir.mkdir('tmpdir')
    mario_folder.chdir()
    f = mario_folder.join('touch_file.ini')
    f.write(TOUCH_FILE)
    cli.mariobros(
            targets=['touched-11-22.file'], mariofile='touch_file.ini', local_scheduler=True
    )
    created_files = sorted(glob.glob('touched*'))
    assert created_files == ['touched-11-22.file', 'touched-11.file', 'touched-22.file']
    cli.mariobros(
            targets=['touched-11-22.file', ], mariofile='touch_file.ini', local_scheduler=True,
            dry_run=True, workers=2
    )
    cli.mariobros(
            targets=['touched-11-22.file', ], mariofile='touch_file.ini', local_scheduler=True,
            print_ns=True
    )

    with pytest.raises(AssertionError):
        cli.mariobros(targets=['touched-11-22.file'.encode('utf-8')])


def test_cli(tmpdir):
    mario_folder = tmpdir.mkdir('tmpdir')
    mario_folder.chdir()
    f = mario_folder.join('touch_file.ini')
    f.write(TOUCH_FILE)

    runner = click.testing.CliRunner()
    mariofile = os.path.join(mario_folder.dirname, 'tmpdir/touch_file.ini')
    args = shlex.split('-f {} --local-scheduler touched-11-22.file'.format(mariofile))
    # split casts the args to str in python2
    args = [str(a) for a in args]
    result = runner.invoke(cli.main, args=args)
    assert not result.exception
    args = shlex.split('-f {} --local-scheduler'.format(mariofile))
    result = runner.invoke(cli.main, args=args)
    assert not result.exception
