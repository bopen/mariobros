# -*- coding: utf-8 -*-

# python 2 support via python-future
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import dict, int, open, str, super

import atexit
import collections
import logging
import os
import re
import subprocess
import uuid

import click
import future.utils
import luigi
import mako.template


LOGGER = logging.getLogger('luigi-interface')

TEMPLATE = """% for var_def, val_def in default_namespace.items():
    % if var_def not in ['action_template', 'sources_repls', 'target_pattern']:
${var_def} = ${val_def}
    %endif
% endfor

% if default_namespace['target_pattern']:
${default_namespace['target_pattern']}: ${default_namespace['sources_repls']}
    ${default_namespace['action_template']}
% endif
% for task_name, section_namespace in section_namespaces.items():
    % if task_name != 'DEFAULT':
[${task_name}]
        %for var, val in section_namespaces[task_name].items():
            % if var not in ['action_template', 'sources_repls', 'target_pattern']:
${var} = ${val}
            % endif
        % endfor
${section_namespace['target_pattern']}: ${section_namespace['sources_repls']}
    ${section_namespace['action_template']}
    % endif

% endfor
"""


class TupleOfStr(tuple):
    """A tuple with a special str representation to be used in rules."""

    def __str__(self):
        return ' '.join(str(item) for item in self)

    def __getitem__(self, key):
        value = super(TupleOfStr, self).__getitem__(key)
        if isinstance(key, slice):
            value = self.__class__(value)
        return value

    def __getslice__(self, i, j):
        value = super(TupleOfStr, self).__getslice__(i, j)
        return self.__class__(value)


class ExistingFile(luigi.ExternalTask):
    """Define Luigi External Task class for existing files requires."""

    target = luigi.Parameter()

    def output(self):
        return luigi.LocalTarget(self.target)


class ReRuleTask(luigi.Task):
    """Define Luigi task class through regular expression.
    """
    # target_pattern = ''
    # sources_repls = []

    # action_namespace = {}
    # action_template = ''

    @staticmethod
    def factory(
            name, target_pattern, sources_repls=(), action_template='', action_namespace={},
            priority=0, worker_timeout=None, resources={}, disabled=False, dry_run_suffix=''):
        """Create Luigi task class.

        :param str name: Task name.
        :param str target_pattern: Target pattern.
        :param list sources_repls: List of source replacements.
        :param str action_template: Action template.
        :param dict action_namespace: Action namespace.
        :param int priority: Priority Luigi task metadata.
        :param int worker_timeout: Worker timeout Luigi task metadata.
        :param dict resources: Resources Luigi task metadata.
        :param bool disabled: Disabled Luigi task metadata.
        :rtype: subclass_of_ReRuleTask
        """
        # FIXME: move class init code to init method?
        if not target_pattern.startswith('(?<![^/])'):
            target_pattern = '(?<![^/])' + target_pattern
        if not target_pattern.endswith('$'):
            target_pattern += '$'
        if action_template.strip() == '':
            action_template = 'echo "${sources} -> ${target}"'
        _target_pattern = re.compile(target_pattern)
        return type(future.utils.native_str(name), (ReRuleTask,), locals())

    @classmethod
    def match(cls, target):
        return bool(cls._target_pattern.search(target))

    target = luigi.Parameter()

    def render_sources(self):
        return TupleOfStr(self._target_pattern.sub(repl, self.target) for repl in self.sources_repls)

    def render_action(self):
        sources = self.render_sources()
        match = self._target_pattern.match(self.target)
        target_namespace = dict(target=self.target, sources=sources, match=match)
        return render_template(self.action_template, target_namespace, default_namespace=self.action_namespace)

    def output(self):
        return luigi.LocalTarget(self.target + self.dry_run_suffix)

    def requires(self):
        required = []
        for source in self.render_sources():
            for task_rule in ReRuleTask.__subclasses__():
                if task_rule.match(source):
                    required.append(task_rule(target=source))
                    break
            else:
                required.append(ExistingFile(source))
        return required

    def run(self):
        cmd = self.render_action()
        if self.dry_run_suffix:
            # log intended command line but touch the dry_run target instead
            LOGGER.info(cmd)
            cmd = 'touch ' + self.target + self.dry_run_suffix
            # register the dry_run target removal at program exit
            atexit.register(self.remove_dry_run_file)
        cmd = ['/bin/bash', '-c', cmd]
        LOGGER.info('COMMAND: {}'.format(cmd))
        subprocess.check_call(cmd)

    def remove_dry_run_file(self):
        subprocess.call('rm -f ' + self.target + self.dry_run_suffix, shell=True)


def render_template(template, local_namespace, default_namespace={}):
    """Return the rendered template merging local and default namespaces.

    :param str template: Template.
    :param dict local_namespace: Local namespace.
    :param dict default_namespace: Default namespace.
    :rtype: str
    """
    namespace = default_namespace.copy()
    namespace.update(local_namespace)
    return mako.template.Template(template, strict_undefined=True).render(**namespace)


def render_namespace(namespace, default_namespace={}, skip_names=('action_template',)):
    """Return Render section namespaces with default section namespaces also.

    :param dict namespace: Section namespace.
    :param dict default_namespace: default section namespace.
    :param list skip_names: Namespace names to skip in the render process.
    :rtype: dict
    """
    torender_namespace = {k: v for k, v in namespace.items() if k not in skip_names}
    rendered_namespace = {k: v for k, v in namespace.items() if k in skip_names}
    while len(torender_namespace):
        loop = True
        for key, value_template in list(torender_namespace.items()):
            try:
                value = render_template(value_template, rendered_namespace, default_namespace)
                torender_namespace.pop(key)
                rendered_namespace[key] = value
                loop = False
            except NameError:
                pass
        if loop:
            raise NameError("Can't render: {!r}".format(torender_namespace))
    return collections.OrderedDict((k, rendered_namespace[k]) for k in namespace)


def register_tasks(namespaces, default_namespace={}, dry_run_suffix=''):
    """Return a Luigi task class after parsed Luigi task metadata.

    :param dict namespaces: Task namespaces.
    :param dict default_namespace: Default namespaces.
    :param bool dry_run_suffix: Suffix to be added to file created during dry run.
    :rtype: iterable
    """

    for task_name, namespace in namespaces.items():
        action_namespace = default_namespace.copy()
        action_namespace.update(namespace)
        task_namespace = {k: namespace[k] for k in ['target_pattern', 'sources_repls', 'action_template'] if
                          k in namespace}
        task_namespace['sources_repls'] = task_namespace['sources_repls'].split()
        # luigi attributes
        task_namespace['resources'] = {k.partition('_')[2]: int(v) for k, v in namespace.items() if
                                       k.startswith('resources_')}
        task_namespace.update(
            {k: int(namespace[k]) for k in ['priority', 'disabled', 'worker_timeout'] if k in namespace})
        yield ReRuleTask.factory(task_name, dry_run_suffix=dry_run_suffix, action_namespace=action_namespace, **task_namespace)


class ConfigurationFileError(Exception):
    pass


def parse_statements(stream):
    """Remove blank line and trailing comments from a string.

    :param iterable stream: Mariofile stream.
    :rtype: iterable
    """
    statement = ''
    for raw_line in stream:
        # remove trailing comments, spaces and new line
        line = raw_line.partition('#')[0].rstrip()
        if re.match(r'^\s+', line):
            statement += '\n' + line
        else:
            if statement:
                yield statement
            statement = line
    if statement:
        yield statement


def parse_section_body(stream):
    """Parse the body of a section and return the section namespace.

    :param iterable stream: Mariofile stream.
    :rtype: dict
    """
    namespace = collections.OrderedDict([
        ('target_pattern', ''),
        ('sources_repls', ''),
        ('action_template', ''),
    ])
    for statement in parse_statements(stream):
        if '=' in statement.partition('\n')[0]:
            name, _, expression_template = [s.strip() for s in statement.partition('=')]
            namespace[name] = expression_template
        elif ':' in statement.partition('\n')[0]:
            if namespace['target_pattern']:
                raise ConfigurationFileError('Section must have only one rule')
            target_sources, _, action_template = statement.strip().partition('\n')
            namespace['action_template'] = action_template
            target_pattern, _, sources = target_sources.partition(':')
            namespace['sources_repls'] = sources.strip()
            namespace['target_pattern'] = target_pattern.strip()
        else:
            raise ConfigurationFileError('Statement not an assignment nor a rule: {!r}'.format(statement))
    return namespace


def parse_sections(stream):
    """Parse a Mariofile and return a dictionary with the section name as the key and the section
    content as the value.

    :param iterable stream: Mariofile stream.
    :rtype: tuple
    """
    section, body_stream = 'DEFAULT', []
    for line_number, line in enumerate(stream, 1):
        match = re.match(r'^\[(.*)\](.*)$', line)
        if match:
            section_name = match.group(1).strip()
            garbage = match.group(2).strip()
            if not future.utils.isidentifier(section_name):
                raise ConfigurationFileError('Invalid section name at line {}: {!r}'.format(
                    line_number, match.group(0)))
            if garbage:
                raise ConfigurationFileError('Garbage after section name at line {}: {!r}'.format(
                    line_number, match.group(0)))
            else:
                yield section, body_stream
                section = match.group(1)
                body_stream = []
        else:
            body_stream += [line]
    yield section, body_stream


def parse_include(raw_lines):
    """Parse the intestation of the raw_lines and return a list of filepaths to be included.

    :param iterable raw_lines: Mariofile raw_lines.
    :rtype: (list, iterable)
    """
    filepaths = []
    current_line = 0
    # workaround for files with only includes and without newline at the end of the file.
    raw_lines += '\n'
    for current_line, raw_line in enumerate(raw_lines):
        line = raw_line.partition('#')[0].rstrip()
        include_match = re.match(r'^include\s+(.*)\s*$', line)
        if not line.strip():
            continue
        elif include_match:
            filepaths.append(include_match.group(1))
        else:
            break
    return filepaths, current_line


def parse_config(raw_lines, cwd='.'):
    """Parse the input Mariofile and the included Mariofiles recursively and return a dictionary
    with the section name as the key and the section namespace as the value.

    :rtype: dict
    """
    include_paths, end_include_line = parse_include(raw_lines)
    section_namespaces = collections.OrderedDict()
    for include_path in include_paths:
        for section, section_namespace in parse_config_file(include_path, cwd=cwd).items():
            namespace = section_namespaces.setdefault(section, collections.OrderedDict())
            namespace.update(section_namespace)
    for section, body_stream in parse_sections(raw_lines[end_include_line:]):
        namespace = section_namespaces.setdefault(section, collections.OrderedDict())
        namespace.update(parse_section_body(body_stream))
    return section_namespaces


def parse_config_file(file_path, cwd='.'):
    file_path = os.path.join(cwd, file_path)
    file_cwd = os.path.dirname(file_path)
    with open(file_path) as stream:
        return parse_config(stream.read().splitlines(True), cwd=file_cwd)


def print_namespaces(default_namespace, section_namespaces):
    template = mako.template.Template(TEMPLATE)
    namespaces = template.render(default_namespace=default_namespace, section_namespaces=section_namespaces)
    return namespaces


def parse_mariofile(mariofile='mario.ini'):
    section_namespaces = parse_config_file(mariofile)
    default_namespace = render_namespace(section_namespaces['DEFAULT'])
    rendered_namespaces = collections.OrderedDict((k, render_namespace(v, default_namespace)) for k, v in section_namespaces.items())
    return section_namespaces, default_namespace, rendered_namespaces


def mario(rendered_namespaces, default_namespace, targets=('default',), dry_run=False):
    """Generate Luigi tasks' file from Mariofile and Luigi template file"""
    dry_run_suffix = '-dry_run-' + str(uuid.uuid4()) if dry_run else ''
    rendered_namespaces = collections.OrderedDict(reversed(list(rendered_namespaces.items())))
    tasks = list(register_tasks(rendered_namespaces, default_namespace=default_namespace, dry_run_suffix=dry_run_suffix))
    target_tasks = []
    for target in targets:
        for task_rule in tasks:
            if task_rule.match(target):
                target_tasks.append(task_rule(target=target))
                break
    return target_tasks


def mariobros(targets=('default',), mariofile='mario.ini', print_ns=False, dry_run=False, workers=1, **kwargs):
    """Main mariobros entry point. Parse the configuration file and launch the build of the targets.

    :param sequence targets:
    :param str mariofile:
    :param bool print_ns:
    :param bool dry_run:
    :param int workers:
    :param dict kwargs: Passed to the luigi.build function.
    """
    if dry_run and workers > 1:
        workers = 1
        LOGGER.warning('Dry run is incompatible with multiprocessing. Setting --workers=1')
    section_namespaces, default_namespace, rendered_namespaces = parse_mariofile(mariofile)
    if print_ns:
        namespaces = print_namespaces(default_namespace, section_namespaces)
        print(namespaces)
    else:
        target_tasks = mario(rendered_namespaces, default_namespace, targets=targets, dry_run=dry_run)
        luigi.build(target_tasks, workers=workers, **kwargs)


@click.command()
@click.argument('targets', nargs=-1, type=click.Path())
@click.option(
    '--file', '--mariofile', '-f', default='mario.ini',
    help='Main configuration file', type=click.Path(exists=True, dir_okay=False))
@click.option(
    '--logging_conf_file', default=None,
    help='Logging configuration file', type=click.Path(exists=True, dir_okay=False))
@click.option('--workers', default=1, help='Number of workers', type=int)
@click.option('--local-scheduler', is_flag=True)
@click.option('--print-ns', is_flag=True)
@click.option('--dry-run', '-n', is_flag=True, help="Don't actually run any commands; just print them.")
def main(targets, **kwargs):
    if not targets:
        targets = ('default',)
    mariobros(targets, **kwargs)
