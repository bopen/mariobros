Mariofile writing
=================

The mariofiles are structured in several tasks:
The default task is the one defined at the top of the file. In this section there are definitions of the variables and the definition
 of the task. The variables defined in the default section are global variables. The default task is executed when no other
 task is required.
The other tasks have local variables and the task defined as explained later.
The variables are defined as follow.

    variable_name = variable_value

The tasks are defined as follow:

    [task_name]
    task_variable_name = task_variable_value
    target: source1 source2 source3 ...
        task_command

In the task_command you can call the target name and the sources name with ${target} and ${sources[i]} where i is an index or a python slice.
In the curly brackets you can execute python code.
You can specify the required resources for the single tasks setting the local variables "resources_cpu_cores" and "resources_memory_kb".
You can match parts of the target name with parts of the sources name with python regular expression syntax.
For example:

    [task_name]
    resources_cpu_cores = 2
    resources_memory_kb = 2000
    (.*)-(.*).txt: \1.txt \2.txt
        touch ${target}

This task match a target like "first-second.txt" with 2 source files named "first.txt" and "second.txt". \1 represent the first match
and \2 represent the second match. To run this task 2 cpus and 2000 kb of ram are required.

At the top of the mariofile there is the include section. You can include other mariofiles in this way:

    include mariofile_name.ini

The global variables of the included mariofile will be added at the top of the mariofile.
The tasks of the included mariofile will be added at the end of the mariofile.
If there are variables or tasks with the same names, only the top level one will be included.

Mario execution
===============

The Mario command line is

    mario --help
    Usage: mario [OPTIONS] [TARGETS]...
    Options:
      -f, --mariofile, --file FILE  Main configuration file
      -p, --port INTEGER            Set `luigi.build` scheduler_port parameter.
      --workers INTEGER             Set the number of workers
      --local-scheduler             Run local scheduler.
      --print-ns                    Print namespaces: Print the MarioFile with the
                                    included tasks and variables

      -n, --dry-run                 Don't actually run any commands; just print
                                    them.

      --help                        Show this message and exit.

All the mario options and arguments are optional. The default task request is DEFAULT. The default mariofile is mario.ini.
With --dry-run flag it doesn't actually run any commands; just print them.

First of all you have to run "luigid" from the python virtualenv. You have to run it from the directory where there is
client.cfg file. In this file you can configure the total required resources and the db path for the status file. An example of client.cfg is:

    [resources]
    memory_kb = 32000000
    cpu_cores = 20

    [scheduler]
    record_task_history = True
    state_path = /usr/local/var/luigi-state.pickle

    [task_history]
    db_connection = sqlite:////path/to/db/luigi-task-hist.db

Then you can run "mario" script with the command line described above.

You can visualize a scheduler in localhost:8082 address. There will be a list of the tasks and a tree diagram of the processing.