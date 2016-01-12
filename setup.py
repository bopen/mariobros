
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='mariobros',
    version='0.1',
    description='Simple configuration for Spotify Luigi.',
    long_description=long_description,
    url='https://github.com/bopen/mariobros',
    author='B-Open Solutions srl',
    author_email='info@bopen.eu',
    license='Proprietary',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: System :: Monitoring',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=[
        'click',
        'mako',
        'future',
        'luigi',
        'pytest',
        'mock',
        'sqlalchemy',
    ],
    extras_require={
        'dev': [
            'check-manifest',
            'pytest-cov',
            'pytest-flakes',
            'pytest-pep8',
            'pytest-pylint',
            'tox',
            'sphinx',
            'sphinx_rtd_theme',
            'ipython',
            'ipdb',
        ],
    },
    entry_points={
        'console_scripts': [
            'mario=mariobros.mario:main',
        ],
    },
)
