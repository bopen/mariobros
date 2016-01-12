MarioBros
=========

Simple configuration language for Spotify Luigi.

Master branch status:

.. image:: https://travis-ci.org/bopen/mariobros.svg?branch=master
    :target: https://travis-ci.org/bopen/mariobros
    :alt: Build Status on Travis CI

.. image:: https://coveralls.io/repos/bopen/mariobros/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/bopen/mariobros
    :alt: Coverage Status on Coveralls

Install
=======

install in the current python environment::

    python setup.py install

Test
====

run all tests::

    py.test -v tests

Usage
=====

see online help::

    mario --help

run mariobros with ./mario.ini config file and 'default' target::

    mario

Develop
=======

Develop::

    python setup.py develop
    pip install -e .[dev]

sphinx-build documentation::

    sphinx-build doc/ doc/html

coverage::

    py.test -v --cov mariobros --cov-report html tests
    open htmlcov/index.html

pep8/flakes::

    py.test -v --pep8 --flakes mariobros tests

version testing::

    tox

run luigid in background with logging::

    luigid > luigid.log 2>&1 &

some minimal test configuration::

    cd tests
    cat mario.ini
    mario
