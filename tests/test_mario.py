# -*- coding: utf-8 -*-

# python 2 support via python-future
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import dict, next, str

import collections
import os

from mock import patch, mock_open
import luigi
import pytest

from mariobros import mario


def test_TupleOfStr():
    tuple_of_strings = ('one', 'two', 'three')
    assert mario.TupleOfStr(tuple_of_strings) == tuple_of_strings
    assert str(mario.TupleOfStr(tuple_of_strings)) == 'one two three'
    assert mario.TupleOfStr(tuple_of_strings)[0] == 'one'
    assert mario.TupleOfStr(tuple_of_strings)[1:] == ('two', 'three')
    assert str(mario.TupleOfStr(tuple_of_strings)[1:]) == 'two three'


class test_ExistingFile():
    existing_file = mario.ExistingFile(__file__)
    assert existing_file.output().exists()


def test_render_template():
    template = '${global_name}-${local_name}'
    global_ns = {'global_name': 'GLOBAL'}
    local_ns = {'local_name': 'LOCAL'}
    rendered = mario.render_template(template, global_ns, local_ns)
    assert rendered == 'GLOBAL-LOCAL'


def test_render_namespace():
    assert mario.render_namespace({'key': 'value'}) == {'key': 'value'}
    assert mario.render_namespace({'key': '${value}'}, {'value': '3'}) == {'key': '3'}
    small_namespace = collections.OrderedDict({'key': '${value}', 'value': '3'})
    assert mario.render_namespace(small_namespace) == {'key': '3', 'value': '3'}
    big_namespace = collections.OrderedDict({'key': '${value}', 'value': '${meta}', 'meta': '3'})
    assert mario.render_namespace(big_namespace) == {'key': '3', 'value': '3', 'meta': '3'}
    with pytest.raises(NameError):
        mario.render_namespace({'a': '${b}'})
    with pytest.raises(NameError):
        mario.render_namespace({'a': '${b}', 'b': '${a}'})
    assert mario.render_namespace({'a': '${b}'}, skip_names=['a']) == {'a': '${b}'}


NAMESPACES = collections.OrderedDict([
    ('rule1', {
        'target_pattern': '(.*).target',
        'sources_repls': '\\1.source',
        'action_template': 'action -o ${target} ${sources}',
    }),
    ('rule2', {
        'resources_cpu': 2,
        'resources_mem': 4,
        'priority': 20,
        'target_pattern': '(.*).source',
        'sources_repls': '\\1.orig',
        'action_template': 'touch ${target}',
    }),
])


def test_ReRuleMixin():
    dry_run_suffix = '-test'
    task_rules = list(mario.register_tasks(NAMESPACES, dry_run_suffix=dry_run_suffix))

    task_rule1 = task_rules[0]
    assert task_rule1.match('file.target')
    assert not task_rule1.match('wrong')
    task1 = task_rule1(target='file.target')
    assert task1.render_sources() == ('file.source',)
    assert task1.render_action() == 'action -o file.target file.source'

    output = task1.output()
    assert isinstance(output, luigi.Target)
    assert output.path == 'file.target' + dry_run_suffix

    requires = task1.requires()
    assert len(requires) == 1
    assert requires[0].target == 'file.source'

    task1.run()

    task_rule2 = task_rules[1]
    task2 = task_rule2(target=requires[0].target)
    requires2 = task2.requires()
    assert len(requires2) == 1
    assert requires2[0].target == 'file.orig'


def test_register_tasks():
    task_rules = mario.register_tasks(NAMESPACES)

    task_rule1 = next(task_rules)
    assert task_rule1.target_pattern == '(?<![^/])(.*).target$'

    task_rule2 = next(task_rules)
    assert task_rule2.resources == {'cpu': 2, 'mem': 4}
    assert task_rule2.priority == 20
    assert task_rule2.match('file.source')


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
    SIMPLE_MARIOFILE_sections = dict(mario.parse_sections(SIMPLE_MARIOFILE.splitlines(True)))
    assert len(SIMPLE_MARIOFILE_sections) == 3
    complex_MARIOFILE_sections = dict(mario.parse_sections(COMPLEX_MARIOFILE.splitlines(True)))
    assert len(complex_MARIOFILE_sections) == 2
    assert sorted(complex_MARIOFILE_sections.keys()) == ['DEFAULT', 'section']
    assert complex_MARIOFILE_sections['DEFAULT'] == ['default text\n', '\n']
    with pytest.raises(mario.ConfigurationFileError):
        dict(mario.parse_sections(GARBAGE_MARIOFILE.splitlines(True)))
    with pytest.raises(mario.ConfigurationFileError):
        dict(mario.parse_sections(INVALID_SECTION_MARIOFILE.splitlines(True)))
    more_complex_MARIOFILE_sections = dict(mario.parse_sections(MORE_COMPLEX_MARIOFILE.splitlines(True)))
    more_complex_MARIOFILE_sections_keys = ['DEFAULT', 'section_one', 'section_two', 'three']
    assert sorted(more_complex_MARIOFILE_sections.keys()) == more_complex_MARIOFILE_sections_keys
    assert more_complex_MARIOFILE_sections['three'] == []


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
    with pytest.raises(mario.ConfigurationFileError):
        mario.parse_section_body(CRASH_MARIOFILE_1.splitlines())
    with pytest.raises(mario.ConfigurationFileError):
        mario.parse_section_body(CRASH_MARIOFILE_2.splitlines())


STRING_PARSE_STATEMENTS = '''
# commento

statement

statement con commento #commento

# altro commento
'''


def test_parse_statements():
    parsed_statement = mario.parse_statements(STRING_PARSE_STATEMENTS.splitlines())
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
    assert mario.parse_section_body(SECTION.splitlines(True)) == output_section
    with pytest.raises(mario.ConfigurationFileError):
        mario.parse_section_body(SECTION_MULTIPLE_RULE.splitlines(True))
    with pytest.raises(mario.ConfigurationFileError):
        mario.parse_section_body(INVALID_CONFIG.splitlines(True))


INCLUDE_FILE = """
include prova.ini\t
include\taltrofile.ini

variable_definition = None
[first_section]
"""
INCLUDE_UNIQUE_FILE = "include prova.ini"


def test_parse_include():
    filepaths, current_line = mario.parse_include(INCLUDE_FILE.splitlines(True))
    assert filepaths == ['prova.ini', 'altrofile.ini']
    assert current_line == 4
    filepaths, current_line = mario.parse_include(INCLUDE_UNIQUE_FILE.splitlines(True))
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


def test_parse_config():
    parsed_MARIOFILE = {
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
    mario.parse_config(MARIOFILE.splitlines(True)) == parsed_MARIOFILE
    parsed_MARIOFILE_include_test = {
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
    with patch('mariobros.mario.open', mock_open(read_data=MARIOFILE_INCLUDE), create=True):
        parsed_MARIOFILE_include = mario.parse_config(MARIOFILE_AND_INCLUDE.splitlines(True))
    for key, value in parsed_MARIOFILE_include.items():
        assert value == parsed_MARIOFILE_include_test[key], print(key)

    parsed_MARIOFILE_multiple_include = {
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

    parsed_MARIOFILE_include = mario.parse_config(MARIOFILE_AND_INCLUDE.splitlines(True), cwd=os.path.dirname(__file__))
    assert parsed_MARIOFILE_include == parsed_MARIOFILE_multiple_include


TOUCH_MARIOFILE = """
default:
    touch

[task]
target: source
    task
"""


def test_print_namespaces():
    section_namespaces = mario.parse_config(TOUCH_MARIOFILE.splitlines(True))
    default_namespace = mario.render_namespace(section_namespaces['DEFAULT'])
    output = """
default:\x20
        touch
[task]
target: source
        task
"""
    # workaround for different behaviour of mako in cpython2, cpython3, pypy2 and pypy3
    assert mario.print_namespaces(default_namespace, section_namespaces).replace('\n\n', '\n').replace('\n\n', '\n') == output


def test_parse_mariofile():
    with patch('mariobros.mario.open', mock_open(read_data=TOUCH_MARIOFILE), create=True):
        section_namespaces, default_namespace, rendered_namespaces = mario.parse_mariofile(TOUCH_MARIOFILE)
    assert section_namespaces['DEFAULT']['action_template'] == '    touch'
    assert default_namespace['action_template'] == '    touch'
    assert rendered_namespaces['DEFAULT']['action_template'] == '    touch'


def test_mario(tmpdir):
    with patch('mariobros.mario.open', mock_open(read_data=TOUCH_MARIOFILE), create=True):
        section_namespaces, default_namespace, rendered_namespaces = mario.parse_mariofile(TOUCH_MARIOFILE)
        touch_tasks = mario.mario(rendered_namespaces, default_namespace)
    assert touch_tasks[0].target == 'default'
    with patch('mariobros.mario.open', mock_open(read_data=TOUCH_MARIOFILE), create=True):
        touch_tasks = mario.mario(rendered_namespaces, default_namespace, targets=['target'])
    assert touch_tasks[0].target == 'target'
    assert touch_tasks[0].name == 'task'
