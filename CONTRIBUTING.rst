Test
----

run all tests::

    py.test -v tests

Develop
-------

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

some minimal test configuration::

    cd tests
    cat mario.ini
    mario
