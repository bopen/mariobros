# -*- coding: utf-8 -*-

# python 2 support via python-future
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import open

import collections
import future.utils
import os
import re


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
                raise ConfigurationFileError("Section must have only one rule")
            target_sources, _, action_template = statement.strip().partition('\n')
            namespace['action_template'] = action_template
            # FIXME: you cannot have SOURCES path with ":" inside, like "s3://".
            target_pattern, _, sources = target_sources.rpartition(':')
            namespace['sources_repls'] = sources.strip()
            namespace['target_pattern'] = target_pattern.strip()
        else:
            raise ConfigurationFileError("Statement not an assignment nor a rule: %r" % statement)
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
                raise ConfigurationFileError(
                    "Invalid section name at line %r: %r" % (line_number, match.group(0))
                )
            if garbage:
                raise ConfigurationFileError(
                    "Garbage after section name at line %r: %r" % (line_number, match.group(0))
                )
            else:
                yield section, body_stream
                section = match.group(1)
                body_stream = []
        else:
            body_stream += [line]
    yield section, body_stream


def parse_include(raw_lines):
    """Parse the heading of the raw_lines and return a list of filepaths to be included.

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

    :param iterable raw_lines: Mariofile per lines.
    :param str cwd: Current working directory.
    :rtype: dict
    """
    include_paths, end_include_line = parse_include(raw_lines)
    section_namespaces = collections.OrderedDict()
    for include_path in include_paths:
        for section, section_namespace in parse_mariofile(include_path, cwd=cwd).items():
            namespace = section_namespaces.setdefault(section, collections.OrderedDict())
            namespace.update(section_namespace)
    for section, body_stream in parse_sections(raw_lines[end_include_line:]):
        namespace = section_namespaces.setdefault(section, collections.OrderedDict())
        namespace.update(parse_section_body(body_stream))
    return section_namespaces


def parse_mariofile(file_path, cwd='.'):
    """Parse input mariofile.

    :param unicode file_path: File path.
    :param str cwd: Current working directory.
    :return: dict
    """
    file_path = os.path.join(cwd, file_path)
    file_cwd = os.path.dirname(file_path)
    with open(file_path) as stream:
        return parse_config(stream.read().splitlines(True), cwd=file_cwd)
