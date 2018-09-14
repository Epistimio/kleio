# -*- coding: utf-8 -*-
# pylint:disable=protected-access
"""
:mod:`kleio.core.io.trial_builder` -- Create experiment from user options
==============================================================================

.. module:: experiment
   :platform: Unix
   :synopsis: Functions which build `Experiment` and `ExperimentView` objects
       based on user configuration.


The instantiation of an `Experiment` is not a trivial process when the user request an experiment
with specific options. One can easily create a new experiment with
`ExperimentView('some_experiment_name')`, but the configuration of a _writable_ experiment is less
straighforward. This is because there is many sources of configuration and they have a strict
hierarchy. From the more global to the more specific, there is:

1. Global configuration:

  Defined by `src.kleio.core.io.resolve_config.DEF_CONFIG_FILES_PATHS`.
  Can be scattered in user file system, defaults could look like:

    - `/some/path/to/.virtualenvs/kleio/share/kleio.core`
    - `/etc/xdg/xdg-ubuntu/kleio.core`
    - `/home/${USER}/.config/kleio.core`

  Note that some variables have default value even if user do not defined them in global
  configuration:

    - `max_trials = src.kleio.core.io.resolve_config.DEF_CMD_MAX_TRIALS`
    - `pool_size = src.kleio.core.io.resolve_config.DEF_CMD_POOL_SIZE`
    - `algorithms = random`
    - Database specific:

      * `database.name = 'kleio'`
      * `database.type = 'MongoDB'`
      * `database.host = ${HOST}`

2. Oríon specific environment variables:

   Environment variables which can override global configuration

    - Database specific:

      * `ORION_DB_NAME`
      * `ORION_DB_TYPE`
      * `ORION_DB_ADDRESS`

3. Experiment configuration inside the database

  Configuration of the experiment if present in the database.
  Making this part of the configuration of the experiment makes it possible
  for the user to execute an experiment by only specifying partial configuration. The rest of the
  configuration is fetched from the database.

  For example, a user could:

    1. Rerun the same experiment

      Only providing the name is sufficient to rebuild the entire configuration of the
      experiment.

    2. Make a modification to an existing experiment

      The user can provide the name of the existing experiment and only provide the changes to
      apply on it. Here is an minimal example where we fully initialize a first experiment with a
      config file and then branch from it with minimal information.

      .. code-block:: bash

          # Initialize root experiment
          kleio init_only --config previous_exeriment.yaml ./userscript -x~'uniform(0, 10)'
          # Branch a new experiment
          kleio hunt -n previous_experiment ./userscript -x~'uniform(0, 100)'

4. Configuration file

  This configuration file is meant to overwrite the configuration coming from the database.
  If this configuration file was interpreted as part of the global configuration, a user could
  only modify an experiment using command line arguments.

5. Command-line arguments

  Those are the arguments provided to `kleio` for any method (hunt, insert, etc). It includes the
  argument to `kleio` itself as well as the user's script name and its arguments.

"""
from collections import OrderedDict
import copy
import logging
import pprint

from kleio.core.io import resolve_config
from kleio.core.io.cmdline_parser import CmdlineParser
from kleio.core.io.database import Database, DuplicateKeyError
from kleio.core.evc.trial_node import TrialNode


log = logging.getLogger(__name__)


class TrialBuilder(object):
    """Builder for :class:`kleio.core.worker.experiment.Experiment`
    and :class:`kleio.core.worker.experiment.ExperimentView`

    .. seealso::

        `kleio.core.io.trial_builder` for more information on the process of building
        experiments.

        :class:`kleio.core.worker.experiment.Experiment`
        :class:`kleio.core.worker.experiment.ExperimentView`
    """

    # pylint:disable=no-self-use
    def fetch_default_options(self):
        """Get dictionary of default options"""
        return resolve_config.fetch_default_options()

    # pylint:disable=no-self-use
    def fetch_env_vars(self):
        """Get dictionary of environment variables specific to Oríon"""
        return resolve_config.fetch_env_vars()

    def fetch_file_config(self, cmdargs):
        """Get dictionary of options from configuration file provided in command-line"""
        return resolve_config.fetch_config(cmdargs)

    def fetch_metadata(self, cmdargs):
        """Infer rest information about the process + versioning"""
        return resolve_config.fetch_metadata(cmdargs)

    def fetch_command_config(self, commandline):

        if not commandline:
            return {}

        cmdline_parser = CmdlineParser()
        return cmdline_parser.parse(commandline)

        positional_index = 0
        argument_name = None
        # todo: resort alphabetically to that reordering of commandline fits to same trial.
        configuration = OrderedDict()
        for arg in commandline:
            if arg.startswith("-"):
                argument_name = arg.lstrip("-")
                configuration[argument_name] = []
            elif argument_name is not None:
                configuration[argument_name].append(arg)
            else:
                configuration["_{}".format(positional_index)] = arg
                positional_index += 1

        for key, value in list(configuration.items()):
            if isinstance(value, list) and len(value) == 1:
                configuration[key] = value[0]

        return configuration

    # ID is defined by trial hash-code
    # If id not in db, start from scratch
    # if --force-no-new, crash (fresh trials can be initiated with kleio save)
    # kleio [-p project name] save [script] [args|]
    #      save VCS, commandline, configuration file and comment
    # kleio [-p project name] exec [trial_name]
    #      save host info, stdout/err and bookkeeping (status, timestamps, etc)
    # kleio [-p project name] branch [--copy] [trial_name] [args|]
    #      copy config of [trial_name] by only modifying given args
    #      If --copy, copy all artifacts and metrics logged so far. Trial can be continued from this
    #      point if script supports resuming.
    #      (possible to add, but not to remove)
    #      (support config file, if args passed in cmd but was in config file, redirect it
    #       accordingly)
    #      (verify consistency of VCS)
    # kleio [-p project name] [script] [args|]
    #      like `kleio exec` but pass entire cmdline
    # kleio [-p project name] status
    # kleio list
    # kleio info [project_name | trial_hash]

    # kleio -p lr_schedule save -n first python main.py --lr 0.1 --epochs 10
    # kleio exec first

    # kleio branch --copy first -n second --lr 0.01 --epochs 20
    # kleio branch --copy second --lr 0.001 --epochs 30

    # kleio branch --copy first -n second_half--lr 0.05 --epochs 20
    # kleio branch --copy second_half --lr 0.01 --epochs 30

    # kleio -p lr_schedule status

    # kleio python main.py --lr 0.1 --epochs 10

    # kleio.client.wrap_argparser

    def fetch_full_config(self, cmdargs, use_db=True):
        """Get dictionary of the full configuration of the trial.

        .. seealso::

            `kleio.core.io.trial_builder` for more information on the hierarchy of
            configurations.

        Parameters
        ----------
        cmdargs:

        use_db: bool
            Use experiment configuration found in database if True. Defaults to True.

        Note
        ----
            This method builds an experiment view in the background to fetch the configuration from
            the database.

        """
        default_options = self.fetch_default_options()
        log.debug("default options:\n{}".format(pprint.pformat(default_options)))
        env_vars = self.fetch_env_vars()
        log.debug("env vars:\n{}".format(pprint.pformat(env_vars)))
        cmdconfig = self.fetch_file_config(cmdargs)
        log.debug("cmdconfig:\n{}".format(pprint.pformat(cmdconfig)))
        metadata = self.fetch_metadata(cmdargs)
        log.debug("metadata:\n{}".format(pprint.pformat(metadata)))

        trial_config = resolve_config.merge_configs(
            default_options, env_vars, cmdconfig, cmdargs, metadata)

        trial_config['configuration'] = self.fetch_command_config(metadata['commandline'])

        # Config has been turned into cmdconfig, pop it out of trial_config
        trial_config.pop('config', None)

        log.debug("trial_config:\n{}".format(pprint.pformat(trial_config)))

        return trial_config

    def build_database(self, cmdargs):
        local_config = self.fetch_full_config(cmdargs)

        log.debug("local config:\n{}".format(pprint.pformat(local_config)))

        db_opts = local_config['database']

        log.debug("db config:\n{}".format(pprint.pformat(db_opts)))

        dbtype = db_opts.pop('type')

        if local_config.get("debug"):
            dbtype = "EphemeralDB"

        # Information should be enough to infer experiment's name.
        log.debug("Creating %s database client with args: %s", dbtype, db_opts)
        try:
            database = Database(of_type=dbtype, **db_opts)
        except ValueError:
            if Database().__class__.__name__.lower() != dbtype.lower():
                raise

            database = Database()

        return database

    def build_view_from(self, cmdargs):
        """Build an experiment view based on full configuration.

        .. seealso::

            `kleio.core.io.trial_builder` for more information on the hierarchy of
            configurations.

            :class:`kleio.core.worker.experiment.ExperimentView` for more information on the
            experiment view object.
        """
        local_config = self.fetch_full_config(cmdargs)
        if 'version' not in local_config:
            raise RuntimeError("Cannot infer script version based on commandline")

        return self.build_view_from_config(local_config)

    def _clean_config(self, config):
        # Pop out configuration concerning databases and resources
        config.pop('database', None)
        config.pop('resources', None)
        config.pop('debug', None)
        config.pop('allow_version_change', None)
        config.pop('allow_host_change', None)
        config.pop('id', None)
        config.setdefault('refers', None)

    def build_view_from_config(self, config):
        config = copy.deepcopy(config)
        self.build_database(config)
        self._clean_config(config)
        trial = TrialNode.build(local=True, **config)
        return TrialNode.view(trial.id)

    def build_from(self, cmdargs):
        """Build a fully configured (and writable) experiment based on full configuration.

        .. seealso::

            `kleio.core.io.trial_builder` for more information on the hierarchy of
            configurations.

            :class:`kleio.core.worker.experiment.Experiment` for more information on the experiment
            object.
        """
        full_config = self.fetch_full_config(cmdargs)

        log.info(full_config)

        # Raise DuplicateKeyError if concurrent trial with identical id
        # is written first in the database.
        return self.build_from_config(full_config)

    def build_from_id(self, cmdargs):
        config = self.fetch_full_config(cmdargs)
        self.build_database(config)

        trial = TrialNode.view(cmdargs['id'])

        if 'version' not in config:
            user_script = resolve_config.fetch_user_script(
                {'commandline': trial.commandline.split(" ")})
            if not user_script:
                raise RuntimeError("Cannot find user script from commandline:"
                                   "\n{trial.commandline}".format(trial=trial))
            config['version'] = resolve_config.infer_versioning_metadata(user_script)
            config['commandline'] = trial.commandline.split(" ")
            config['configuration'] = trial.configuration

        # Branching trial
        if trial.host != config['host'] or trial.version != config['version']:
            return self.branch_from_config(config, trial=trial)

        # Resume trial
        return TrialNode.load(cmdargs['id'])

    def build_from_config(self, config):
        """Build a fully configured (and writable) experiment based on full configuration.

        .. seealso::

            `kleio.core.io.trial_builder` for more information on the hierarchy of
            configurations.

            :class:`kleio.core.worker.experiment.Experiment` for more information on the experiment
            object.
        """
        # Raise DuplicateKeyError if concurrent trial with identical id
        # is written first in the database.
        trial = self.build_view_from_config(config)

        # Starting from scratch
        if trial is None:
            self._clean_config(config)
            return TrialNode.build(**config)

        # Branching trial
        if trial.host != config['host'] or trial.version != config['version']:
            return self.branch_from_config(config, trial=trial)

        # Resume trial
        self._clean_config(config)
        return TrialNode.build(**config)

    def branch_from_config(self, config, trial=None):
        if trial is None:
            trial = self.build_view_from_config(config)
            if trial is None:
                raise RuntimeError("Cannot find trial {trial.short_id}".format(trial=trial))

        if trial.host != config['host'] and not config['allow_host_change']:
            raise RuntimeError("Current host differs from trial "
                               "{trial.short_id}".format(trial=trial))

        if trial.version != config['version'] and not config['allow_version_change']:
            raise RuntimeError("Current code version differs from trial "
                               "{trial.short_id}".format(trial=trial))

        self._clean_config(config)
        return self.branch_leaf(trial.id, **config)

    def branch_leaf(self, trial, timestamp=None, **config):
        try:
            trial = TrialNode.branch(trial.id, timestamp=timestamp, **config)
        except RuntimeError as e:
            if not "Branch already exist with id" in str(e):
                raise

            trial = branch_leaf(TrialNode.load(str(e).split(" ")[-1].strip("'")), **config)

        return trial
