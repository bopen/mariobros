# -*- coding: utf-8 -*-

# python 2 support via python-future
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import dict

import os

import pytest

from mariobros import mariofile

SIMPLE_MARIOFILE = """[section_one]
text one
[section_two]
text two
"""

COMPLEX_MARIOFILE = """default text

[section]    \ntext section
"""

GARBAGE_MARIOFILE = """default

[garbage_section] # garbage
"""

INVALID_SECTION_MARIOFILE = """
# spaces not allowed in section name
[section one]
"""

MORE_COMPLEX_MARIOFILE = """# default

[section_one]
text one
# comment
text two # inline comment
[section_two]
text three
[three]
[DEFAULT]
last"""


def test_parse_sections():
    simple_mariofile_sections = dict(mariofile.parse_sections(SIMPLE_MARIOFILE.splitlines(True)))
    assert len(simple_mariofile_sections) == 3
    complex_mariofile_sections = dict(mariofile.parse_sections(COMPLEX_MARIOFILE.splitlines(True)))
    assert len(complex_mariofile_sections) == 2
    assert sorted(complex_mariofile_sections.keys()) == ['DEFAULT', 'section']
    assert complex_mariofile_sections['DEFAULT'] == ['default text\n', '\n']
    with pytest.raises(mariofile.ConfigurationFileError):
        dict(mariofile.parse_sections(GARBAGE_MARIOFILE.splitlines(True)))
    with pytest.raises(mariofile.ConfigurationFileError):
        dict(mariofile.parse_sections(INVALID_SECTION_MARIOFILE.splitlines(True)))
    more_complex_mariofile_sections = dict(
            mariofile.parse_sections(MORE_COMPLEX_MARIOFILE.splitlines(True))
    )
    more_complex_mariofile_sections_keys = ['DEFAULT', 'section_one', 'section_two', 'three']
    assert sorted(more_complex_mariofile_sections.keys()) == more_complex_mariofile_sections_keys
    assert more_complex_mariofile_sections['three'] == []


CRASH_MARIOFILE_1 = '''
[a]
name
  target:
    a = 1
'''

CRASH_MARIOFILE_2 = '''
[a]
name
    variable = 1
'''


def test_statements():
    with pytest.raises(mariofile.ConfigurationFileError):
        mariofile.parse_section_body(CRASH_MARIOFILE_1.splitlines())
    with pytest.raises(mariofile.ConfigurationFileError):
        mariofile.parse_section_body(CRASH_MARIOFILE_2.splitlines())


STRING_PARSE_STATEMENTS = '''
# commento

statement

statement con commento #commento

# altro commento
'''


def test_parse_statements():
    parsed_statement = mariofile.parse_statements(STRING_PARSE_STATEMENTS.splitlines())
    assert '\n'.join(parsed_statement) == "statement\nstatement con commento"


SECTION = """
variable = 6
target: source
    task
"""

SECTION_MULTIPLE_RULE = """
target1: source1
    task1
target2: source2
    task2
"""

INVALID_CONFIG = """
not a definition
target: source
"""


def test_parse_section_body():
    output_section = {
        'action_template': '    task',
        'sources_repls': 'source',
        'variable': '6',
        'target_pattern': 'target',
    }
    assert mariofile.parse_section_body(SECTION.splitlines(True)) == output_section
    with pytest.raises(mariofile.ConfigurationFileError):
        mariofile.parse_section_body(SECTION_MULTIPLE_RULE.splitlines(True))
    with pytest.raises(mariofile.ConfigurationFileError):
        mariofile.parse_section_body(INVALID_CONFIG.splitlines(True))


INCLUDE_FILE = """
include prova.ini\t
include\taltrofile.ini

variable_definition = None
[first_section]
"""
INCLUDE_UNIQUE_FILE = "include prova.ini"


def test_parse_include():
    filepaths, current_line = mariofile.parse_include(INCLUDE_FILE.splitlines(True))
    assert filepaths == ['prova.ini', 'altrofile.ini']
    assert current_line == 4
    filepaths, current_line = mariofile.parse_include(INCLUDE_UNIQUE_FILE.splitlines(True))
    assert filepaths == ['prova.ini']
    assert current_line == 1


MARIOFILE = """[DEFAULT]
variable = 1

[section_one]
target1: source1
    task1
"""

MARIOFILE_AND_INCLUDE = """
include test_parse_config.ini

[section_include_1]
"""

MARIOFILE_INCLUDE = """
task_cmd = task_command
[section_include]
variable_include_2 = 0
target_include: source_include
\t${task_cmd}
[section_include_1]
variable_include_3 = 3
"""

TOUCH_MARIOFILE = """
DEFAULT:
    touch

[task]
target: source
    task
"""

TEST_PARSE_CONFIG = """
include test_include.ini
variable_default = 1

[section_main]
[section_include_1]
variable_include1 = 3
"""


def test_parse_config(tmpdir):
    parsed_mariofile = {
        'DEFAULT': {
            'action_template': '',
            'sources_repls': '',
            'target_pattern': '',
            'variable': '1'
        },
        'section_one': {
            'action_template': '    task1',
            'sources_repls': 'source1',
            'target_pattern': 'target1'}
    }
    mariofile.parse_config(MARIOFILE.splitlines(True)) == parsed_mariofile
    parsed_mariofile_include_test = {
        'DEFAULT': {
            'action_template': '',
            'sources_repls': '',
            'target_pattern': '',
            'task_cmd': 'task_command',
        },
        'section_include': {
            'variable_include_2': '0',
            'action_template': '\t${task_cmd}',
            'target_pattern': 'target_include',
            'sources_repls': 'source_include',
        },
        'section_include_1': {
            'action_template': '',
            'sources_repls': '',
            'target_pattern': '',
            'variable_include_3': '3',
        }
    }
    mario_folder = tmpdir.mkdir('tmpdir')
    f = mario_folder.join('test_parse_config.ini')
    f.write(MARIOFILE_INCLUDE)
    g = mario_folder.join('test_include.ini')
    g.write('')
    mario_folder.chdir()
    parsed_mariofile_include = mariofile.parse_config(
            MARIOFILE_AND_INCLUDE.splitlines(True),
            cwd=os.path.join(str(mario_folder.dirname), 'tmpdir')
    )
    for key, value in parsed_mariofile_include.items():
        assert value == parsed_mariofile_include_test[key], print(key)

    parsed_mariofile_multiple_include = {
        'DEFAULT': {
            'action_template': '',
            'sources_repls': '',
            'target_pattern': '',
            'variable_default': '1',
        },
        'section_main': {
            'action_template': u'',
            'sources_repls': u'',
            'target_pattern': u''
        },
        'section_include_1': {
            'action_template': '',
            'sources_repls': '',
            'target_pattern': '',
            'variable_include1': '3',
        }
    }
    h = mario_folder.join('test_parse_config.ini')
    h.write(TEST_PARSE_CONFIG)
    parsed_mariofile_include = mariofile.parse_config(MARIOFILE_AND_INCLUDE.splitlines(True),
                                                      cwd=os.path.join(
                                                              str(mario_folder.dirname), 'tmpdir'
                                                      ))
    assert parsed_mariofile_include == parsed_mariofile_multiple_include
