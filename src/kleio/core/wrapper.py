# -*- coding: utf-8 -*-
"""
:mod:`kleio.core.worker.consumer` -- Evaluate objective on a set of parameters
==============================================================================

.. module:: consumer
   :platform: Unix
   :synopsis: Call user's script as a black box process to evaluate a trial.

"""
import logging
import os
import subprocess
import sys
import tempfile

from kleio.core.io.convert import JSONConverter
from kleio.core.io.database import Database
from kleio.core.io.space_builder import SpaceBuilder
from kleio.core.worker.trial import Trial

log = logging.getLogger(__name__)


class Consumer(object):
    """Consume a trial by using it to initialize a black-box box to evaluate it.

    It uses an `Experiment` object to push an evaluated trial, if results are
    delivered to the worker process successfully.

    It forks another process which executes user's script with the suggested
    options. It expects results to be written in a **JSON** file, whose path
    has been defined in a special kleio environmental variable which is set
    into the child process' environment.

    """

    def __init__(self, experiment):
        """Initialize a consumer.

        :param experiment: Manager of this experiment, provides convenient
           interface for interacting with the database.
        """
        log.debug("Creating Consumer object.")
        self.experiment = experiment
        self.space = experiment.space
        if self.space is None:
            raise RuntimeError("Experiment object provided to Consumer has not yet completed"
                               " initialization.")

        # Fetch space builder
        self.template_builder = SpaceBuilder()
        self.template_builder.build_from(experiment.metadata['user_args'])
        # Get path to user's script and infer trial configuration directory
        self.script_path = experiment.metadata['user_script']
        self.tmp_dir = os.path.join(tempfile.gettempdir(), 'kleio')
        os.makedirs(self.tmp_dir, exist_ok=True)

        self.converter = JSONConverter()

    def consume(self, trial):
        """Execute user's script as a block box using the options contained
        within `trial`.

        :type trial: `kleio.core.worker.trial.Trial`

        """
        log.debug("### Create new temporary directory at '%s':", self.tmp_dir)
        with tempfile.TemporaryDirectory(prefix=self.experiment.name + '_',
                                         dir=self.tmp_dir) as workdirname:
            log.debug("## New temp consumer context: %s", workdirname)
            completed_trial = self._consume(trial, workdirname)

        if completed_trial is not None:
            log.debug("### Register successfully evaluated %s.", completed_trial)
            self.experiment.push_completed_trial(completed_trial)
        else:
            log.debug("### Save %s as broken.", trial)
            trial.status = 'broken'
            Database().write('trials', trial.to_dict(),
                             query={'_id': trial.id})

    def _consume(self, trial, workdirname):
        config_file = tempfile.NamedTemporaryFile(mode='w', prefix='trial_',
                                                  suffix='.conf', dir=workdirname,
                                                  delete=False)
        config_file.close()
        log.debug("## New temp config file: %s", config_file.name)
        results_file = tempfile.NamedTemporaryFile(mode='w', prefix='results_',
                                                   suffix='.log', dir=workdirname,
                                                   delete=False)
        results_file.close()
        log.debug("## New temp results file: %s", results_file.name)

        log.debug("## Building command line argument and configuration for trial.")
        cmd_args = self.template_builder.build_to(config_file.name, trial, self.experiment)

        log.debug("## Launch user's script as a subprocess and wait for finish.")
        script_process = self.launch_process(results_file.name, cmd_args)

        if script_process is None:
            return None

        returncode = script_process.wait()

        if returncode != 0:
            log.error("Something went wrong. Check logs. Process "
                      "returned with code %d !", returncode)
            if returncode == 2:
                sys.exit(2)
            return None

        return trial

    def launch_process(self, results_filename, command):
        """Facilitate launching a black-box trial."""
        env = dict(os.environ)
        env['ORION_RESULTS_PATH'] = str(results_filename)
        process = subprocess.Popen(command, env=env)
        returncode = process.poll()
        if returncode is not None and returncode < 0:
            log.error("Failed to execute script to evaluate trial. Process "
                      "returned with code %d !", returncode)
            return None

        return process
