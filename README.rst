******
Kleiṓ
******

------------------------------
Note that this is a prototype. 
------------------------------

Functionalities are not well tested and interface is very likely to change.

-----

|pypi| |py_versions| |license| |rtfd| |codecov| |travis|

.. |pypi| image:: https://img.shields.io/pypi/v/kleio.core.svg
    :target: https://pypi.python.org/pypi/kleio.core
    :alt: Current PyPi Version

.. |py_versions| image:: https://img.shields.io/pypi/pyversions/kleio.core.svg
    :target: https://pypi.python.org/pypi/kleio.core
    :alt: Supported Python Versions

.. |license| image:: https://img.shields.io/badge/License-BSD%203--Clause-blue.svg
    :target: https://opensource.org/licenses/BSD-3-Clause
    :alt: BSD 3-clause license

.. |rtfd| image:: https://readthedocs.org/projects/kleio/badge/?version=latest
    :target: https://kleio.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |codecov| image:: https://codecov.io/gh/Epistimio/kleio/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/Epistimio/kleio
    :alt: Codecov Report

.. |travis| image:: https://travis-ci.org/Epistimio/kleio.svg?branch=master
    :target: https://travis-ci.org/Epistimio/kleio
    :alt: Travis tests

Kleiṓ is an experiment manager, a logging journal of all data describing your
experiments.

Its purpose is to provide an automatic tool to log extensive environment
information, including script's code version, system specification and script
configuration. The logging journal can include statistics manually logged
from within the user's script as well as artifacts and ressources. 

It assumes the computation is entirely deterministic, and if not
deterministic then one of the argument is a seed that makes it fully
reproducible.

Features
========
*As simple and as complex you want*

- Simple and natural
- Minimal and non-intrusive client interface for logging
- Database logging (currently powered by MongoDB_)
- Flexible configuration
- Automatic detection of code or environment change on script resuming
- Support branching experiments to avoid recomputation and minimize log journal
  size
- Inuitive and flexible interface for retrieval and navigation of statistics

.. _MongoDB: https://www.mongodb.com/

Installation
============

Install Kleiṓ (prototype) by running:

``pip install git+https://github.com/epistimio/kleio.git@prototype``

Getting started
===============

Configuring the database
------------------------

TODO

Executing a command
-------------------

Suppose you would execute your command the following way

.. code:: bash

   $ python myscript.py one_pos_arg --some arguments --and some more

To log your execution with Kleiṓ, you simply need to prepend the command
`kleio` at the beginning of the commandline.

.. code:: bash
    
    $ kleio python myscript.py one_pos_arg --some arguments --and some more
    > trial reserved with id: <some-id-string>

You can resume the script by running the same command again or by specifing the
id of the trial.

.. code:: bash

    $ kleio run <some-id-string>

Since Kleiṓ is multiprocess safe, trying to execute the same command
twice concurrently will raise an error.

.. code:: bash

    $ kleio run <some-id-string>
    > TODO: Error message

To allow resuming execution even though the code or the system changed, you
can use the options --allow-code-change, --allow-env-change or
--allow-any-change. In order to ensure full reproducibility, the trial will
actually be branched. The timestamp of branching will be marked in the trial
configuration, so that the change of code or environement can be tracked. Note
that since the trial has been branched, the original one can still be resumed
using the original code version in the original environement. This makes it
possible to compare the effect of code change or environment change.

.. code:: bash

     $ kleio run --allow-any-change python myscript.py one_pos_arg --some arguments --and some more

or

.. code:: bash

    $ kleio exec --allow-any-change <some-id-string>

Logging
-------

Statistics
~~~~~~~~~~

``log_statistic(**kwargs)``

The method is built such that it will turn whatever is passed to it into a dictionary.
Note that you cannot log using positional attributes, you must use named attributes.
This is because the log would be meaningless if we would provide unnamed values.
Statistics can be retrieved from a trial and sorted with respect to any possible key in the log.
Thanks to this, there is no specific timestamp field, and any key such as ``epoch```, ``iteration`` 
or `loss` could be used to sort statistics when analysing a trial.

.. code:: python
 
    from kleio.client.logger import kleio_logger
    
    kleio_logger.log_statistic(some_time='some time', some_value='some value')
    kleio_logger.log_statistic(some_time='some other time', some_value='some other value')
    
Note that a script using ``kleio_logger.log_statistic`` can be executed without ``kleio``.
In such case, the method will only print the logged statistics in terminal, without saving it
in any database.

Artifacts
~~~~~~~~~

``log_artifact(filename, artifact, **kwargs)``

Artifacts are logged in a similar fashion as for statistics, with the slight difference that 
a filename and a file-like object must be passed. Any other named arguments are saved as 
metadata for the artifact. This metadata is particularly usefull when retrieving artifacts based
on special keys, such as fetching ``'weights'`` for ``epoch=10``.

.. code:: python
 
    from kleio.client.logger import kleio_logger

    kleio_logger.log_artifact('some_file_path', some_file_like_object,
                              some_time='some time', some_value='some other value')

Ressources
~~~~~~~~~~

Ressources are not supported yet, but will have a very similar interface as for artifacts.

Reading
-------

Cat
~~~

.. code:: bash

    $ kleio cat <some-id-string>

Tail
~~~~

.. code:: bash

    $ kleio tail -f <some-id-string>

Info
~~~~

.. code:: bash

    $ kleio info <some-id-string>

PDB
~~~

.. code:: bash

    $ kleio pdb <some-id-string>
    
    
List
~~~~

.. code:: bash

    $ kleio ls

Branching
---------

.. code:: bash

    $ kleio branch <some-id-string> --some new-argument-value --new argument

Note that positional arguments cannot be updated by Kleiṓ when branching.

.. code:: bash

    $ kleio branch --timestamp epoch=10 <some-id-string>

Contribute or Ask
=================

Do you have a question or issues?
Do you want to report a bug or suggest a feature? Name it!
Please contact us by opening an issue in our repository below:

- Issue Tracker: `<github.com/epistimio/kleio/issues>`_
- Source Code: `<github.com/epistimio/kleio>`_

Start by starring and forking our Github repo!

Thanks for the support!

License
=======

The project is licensed under the BSD license.
