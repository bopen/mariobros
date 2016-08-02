# -*- coding: utf-8 -*-

# python 2 support via python-future
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import next

import collections
import os

import luigi
import pytest

from mariobros import mario
from mariobros import mariofile


cw_dir = os.path.dirname(__file__)


def test_pretty_unicode():
    assert mario.pretty_unicode(range(3)) == '0 1 2'
    assert mario.pretty_unicode('test') == 'test'


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
        'action_template': 'action -o ${TARGET} ${SOURCES}',
    }),
    ('rule2', {
        'RESOURCES_cpu': 2,
        'RESOURCES_mem': 4,
        'priority': 20,
        'target_pattern': '(.*).source',
        'sources_repls': '\\1.orig',
        'action_template': '',
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

    task2.remove_dry_run_file()


def test_register_tasks():
    task_rules = mario.register_tasks(NAMESPACES)

    task_rule1 = next(task_rules)
    assert task_rule1.target_pattern == '(?<![^/])(.*).target$'

    task_rule2 = next(task_rules)
    assert task_rule2.resources == {'cpu': 2, 'mem': 4}
    assert task_rule2.priority == 20
    assert task_rule2.match('file.source')


TOUCH_MARIOFILE = """
DEFAULT:
    touch

[task]
target: source
    task
"""


def test_print_namespaces():
    section_namespaces = mariofile.parse_config(TOUCH_MARIOFILE.splitlines(True))
    default_namespace = mario.render_namespace(section_namespaces['DEFAULT'])
    output = """
DEFAULT:\x20
        touch
[task]
target: source
        task
"""
    # workaround for different behaviour of mako in cpython2, cpython3, pypy2 and pypy3
    assert mario.print_namespaces(
            default_namespace, section_namespaces
    ).replace('\n\n', '\n').replace('\n\n', '\n') == output


def test_render_config(tmpdir):
    mario_folder = tmpdir.mkdir('tmpdir')
    f = mario_folder.join('render_config.ini')
    f.write(TOUCH_MARIOFILE)
    mario_folder.chdir()
    section_namespaces = mariofile.parse_mariofile('render_config.ini')
    default_namespace, rendered_namespaces = mario.render_config(section_namespaces)
    assert section_namespaces['DEFAULT']['action_template'] == '    touch'
    assert default_namespace['action_template'] == '    touch'
    assert rendered_namespaces['DEFAULT']['action_template'] == '    touch'


def test_mario(tmpdir):
    mario_folder = tmpdir.mkdir('tmpdir')
    f = mario_folder.join('test_mario.ini')
    f.write(TOUCH_MARIOFILE)
    mario_folder.chdir()
    section_namespaces = mariofile.parse_mariofile('test_mario.ini')
    default_namespace, rendered_namespaces = mario.render_config(section_namespaces)
    touch_tasks = mario.mario(rendered_namespaces, default_namespace)
    assert touch_tasks[0].target == 'DEFAULT'
    touch_tasks = mario.mario(rendered_namespaces, default_namespace, targets=['target'])
    assert touch_tasks[0].target == 'target'
    assert touch_tasks[0].name == 'task'
