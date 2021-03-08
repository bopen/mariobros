=========
MarioBros
=========

MarioBros is a Python module to configure `Spotify-Luigi <https://github.com/spotify/luigi>`_ in a makefile-like manner.

Spotify-Luigi is a Python module that helps you build complex pipelines of batch jobs.
It handles dependency resolution, workflow management, visualization etc.
The configuration files will called MarioFiles.

Master branch status:

.. image:: https://travis-ci.org/bopen/mariobros.svg?branch=master
    :target: https://travis-ci.org/bopen/mariobros
    :alt: Build Status on Travis CI

.. image:: https://coveralls.io/repos/bopen/mariobros/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/bopen/mariobros
    :alt: Coverage Status on Coveralls

Writing MarioFile
-----------------

The MarioFiles are structured in several section representing the various tasks.

Task definition
+++++++++++++++

An example of task definition is::

    [task_name]
    target: source1 source2 source3
        task_command

The task name is defined in the square brackets. Target and sources are divided by two points.
In the line below there is the task command.
In the task_command you can call the target name and the sources name with ``${TARGET}`` and ``${SOURCES[i]}`` where ``i``
is an index or a python slice.
In the curly brackets you can execute python code with variables defined upper.
You can match parts of the target name with parts of the sources name with python regular expression syntax.
For example::

    [task_name]
    (.*)-(.*)-(.*).txt: \1.txt \2.txt \3.txt
        task_command --output ${TARGET} --first-input ${SOURCES[0]} --other-inputs ${SOURCES[1:]}

This task match a target like ``first-second-third.txt`` with 3 source files named ``first.txt``, ``second.txt`` and ``third.txt``.
``\1`` represent the first match, ``\2`` represent the second match and ``\3`` the third one.

You can also define task variables and use them below. You have to define them below the task name as follow::

    [task_name]
    variable1 = value1
    variable2 = value2
    target: source
        task_command -o ${TARGET} -i ${SOURCES} --par1 ${variable1} --par2 ${variable2}


Default section
+++++++++++++++

The default section is the one defined, without specifying the name, at the top of the file. In this section there are definitions of the global variables
and the definition of the default task. The default task is executed when no other task is requested::

    global_variable1 = value1
    global_variable2 = value2

    default_target: source1 source2
        default_task_command

At the top of the file you can include other MarioFiles with the path in this way::

    include mariofile_path.ini

The global variables of the included MarioFile will be added at the top of the MarioFile.
The tasks of the included MarioFiles will be added at the end of the MarioFile.
If there are variables or tasks with the same names, only the top level one will be included.

Summing up, a typical MarioFile will look like this::

    include included_mariofile.ini

    global_var1 = value1
    global_var2 = value2

    (.*)-main_target.out: \1-\1-task1
        default_task -o ${SOURCES} -i ${TARGET}

    [task_1]
    RESOURCES_CPU = 4
    (.*)-(.*)-task1: source1 source2
        task_1 -o ${TARGET} -i ${SOURCES} -j ${RESOURCES_CPU}

Executing Mario
---------------

The Mario command line is:

.. code-block:: console

    $ mario --help
    Usage: mario [OPTIONS] [TARGETS]...

    Options:
      -f, --file, --mariofile PATH  Main configuration file
      -p, --port INTEGER            Set `luigi.build` scheduler_port parameter.
      --workers INTEGER             Set the number of workers
      --local-scheduler             Run local scheduler.
      --print-ns                    Print namespaces: Print the MarioFile with the
                                    included tasks and variables
      -n, --dry-run                 Don't actually run any commands; just print
                                    them.
      --help                        Show this message and exit.

With:

    1. All the mario options and arguments are optional.
    2. The default task request is ``[DEFAULT]``.
    3. The default mariofile is ``mario.ini``.
    4. With ``--print-ns`` flag it print the whole MarioFile with the included tasks and variables.
    5. With ``--dry-run`` flag it doesn't actually run any commands; just print them.

With external scheduler
+++++++++++++++++++++++

First of all you have to run ``luigid``::

    $ luigid

Then you can run ``mario`` script with the command line described above::

    $ mario

In this way mario will execute the default target with mario.ini as MarioFile.
You can also request a specific target with a MarioFile different from mario.ini as follow::

    $ mario -f my_mariofile.ini target.out

You can visualize a scheduler in `localhost:8082 <http://localhost:8082/>`_ address.
There will be a list of the tasks and a tree diagram of the processing.

With local scheduler
++++++++++++++++++++

If you don't need to visualize the scheduler you can run ``mario`` without ``luigid`` running and with the local scheduler as follow::

    $ mario --local-scheduler

Luigi configuration file
------------------------

Luigi can store the statistic of the processing and can manage the resources.
You have to configure luigi writing *client.cfg* file and then launch ``luigid`` from the *client.cfg* directory.

Writing statistics in database
++++++++++++++++++++++++++++++

In *client.cfg* file you can configure the db path for the statistics. An example of *client.cfg* is::

    [scheduler]
    record_task_history = True
    state_path = /path/to/luigi-state.pickle

    [task_history]
    db_connection = sqlite:////path/to/db/luigi-task-hist.db

Resources management
++++++++++++++++++++

You can also specify the required resources for the single tasks.

You have to define the available resources in the *client.cfg* file defining the ``[resources]`` section as follow::

    [resources]
    cpus = 64

You can specify required resources for the single tasks setting the local task variables ``RESOURCES_RESOURCE_NAME``
where ``RESOURCE_NAME`` is the name of the resource defined in the *client.cfg*, for example::

    [task_name]
    RESOURCES_cpus = 4
    target: sources
        task_command -j ${RESOURCES_cpus}

The request resource is ``4`` for ``cpus``.

Install
-------

install in the current python environment::

    pip install mariobros

