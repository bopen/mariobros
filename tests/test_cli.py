import glob

from mariobros import cli

TOUCH_FILE = r"""touched-([^-.]+)-([^-.]+).file: touched-\1.file touched-\2.file
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
            targets=['touched-11-22.file', ], mariofile='touch_file.ini', local_scheduler=True
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
