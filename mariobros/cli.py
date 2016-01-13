# -*- coding: utf-8 -*-

# python 2 support via python-future
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import dict, int, open, str, super

import click
from mariobros import mario


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
        targets = ('DEFAULT',)
    mario.mariobros(targets, **kwargs)
