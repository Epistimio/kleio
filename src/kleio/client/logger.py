# -*- coding: utf-8 -*-
"""
:mod:`kleio.client` -- Helper function for returning results from script
==========================================================================

.. module:: client
   :platform: Unix
   :synopsis: Provides functions for communicating with `kleio.core`.

"""
import io
import pickle
import os
import logging
import pprint


python_logger = logging.getLogger(__name__)


class Logger(object):
    def __init__(self):
        self.trial = TrialNode.load(KLEIO_TRIAL_ID)
        if self.trial is None:
            raise RuntimeWarning(
                "Trial with id '{}' could not be found in database".format(KLEIO_TRIAL_ID))

    def log_statistic(self, **statistics):
        self.trial.add_statistic(**statistics)

    def log_artifact(self, filename, artifact, backup_path='.', **attributes):
        self.trial.add_artifact(filename, artifact, **attributes)

    def load_statistic(self, query):
        if isinstance(query, str):
            return self.trial.statistics[query]

        rvals = {}
        query = flatten(query)
        for key, value in query.items():
            rvals[key] = self.trial.statistics[key][value]

        self.trial.statistics.training_loss.epoch[-1]
        self.trial.statistics.epoch[-1]
        # would return training_loss, validation_loss, etc, all aggregated
        return unflatten(rvals)

    def load_artifacts(self, filename, query):
        for f, metadata in self.trial.get_artifacts(filename, query):
            yield (RemoteFileWrapper(f), metadata)




class AnalyzeLogger(Logger):
    def __init__(self, trial_id):
        self.trial = TrialNode.load(trial_id)
        if self.trial is None:
            raise RuntimeWarning(
                "Trial with id '{}' could not be found in database".format(trial_id))

    def insert_statistic(self, timestamp, **statistics):
        statistics.setdefault('tags', ";".join(kleio_logger.trial.tags))
        from kleio.core.io.database import DuplicateKeyError
        try:
            self.trial.add_statistic(creator=KLEIO_TRIAL_ID, timestamp=timestamp, **statistics)
        except DuplicateKeyError:
            self.trial.update()
            self.insert_statistic(timestamp, **statistics)

    def insert_artifact(self, filename, artifact, backup_path='.', **attributes):
        raise NotImplementedError()
        self.trial.add_artifact(filename, artifact, **attributes)

    def load_config(self):
        return self.trial.configurations

    def load_statistic(self, query):
        raise NotImplementedError()
        if isinstance(query, str):
            return self.trial.statistics[query]

        rvals = {}
        query = flatten(query)
        for key, value in query.items():
            rvals[key] = self.trial.statistics[key][value]

        self.trial.statistics.training_loss.epoch[-1]
        self.trial.statistics.epoch[-1]
        # would return training_loss, validation_loss, etc, all aggregated
        return unflatten(rvals)

    def load_artifacts(self, filename, query, backup_path="."):
        for f, metadata in self.trial.get_artifacts(filename, query):
            yield (RemoteFileWrapper(f), metadata)


class BackupLogger(object):
    def __init__(self, trial_id=None):
        try:
            from kleio.core.io.trial_builder import TrialBuilder
            from kleio.core.evc.trial_node import TrialNode
            TrialBuilder().build_database({})  # {'debug': KLEIO_DEBUG_MODE})
            self.trial = TrialNode.load(trial_id)
        except Exception as e:
            print(str(e))
            self.trial = None

    def log_statistic(self, **statistics):
        pprint.pprint(statistics)

    def insert_statistic(self, **statistics):
        pprint.pprint(statistics)

    def insert_statistic(self, timestamp, **statistics):
        statistics.setdefault('tags', self.trial.tags)
        print("If using kleio, would insert at runtime_timestamp {}".format(timestamp))
        pprint.pprint(statistics)

    def load_config(self):
        if self.trial is None:
            return {}
        return self.trial.configurations

    def log_artifact(self, filename, artifact, backup_path='.', **attributes):
        python_logger.warning("Cannot log artifact '{}' if `kleio` is not used".format(filename))
        pprint.pprint(attributes)

        # with open(os.path.join(backup_path, filename), 'wb') as f:
        #     artifact.seek(0)
        #     f.write(artifact.read())

        # with open(os.path.join(backup_path, filename + ".metadata"), 'wb') as f:
        #     pickle.dump(attributes, f)

    def load_statistic(self, query):
        python_logger.warning("Cannot load statistics if `kleio` is not used")
        return {}

    def load_artifacts(self, filename, query):
        if self.trial is None:
            python_logger.warning("Cannot load artifacts '{}' if `kleio` is not used".format(filename))
            return []

        for f, metadata in self.trial.get_artifacts(filename, query):
            yield (RemoteFileWrapper(f), metadata)


class RemoteFileWrapper(object):
    def __init__(self, remote_file, chunk_size=255 * 1024):
        self.remote_file = remote_file
        self.chunk_size = chunk_size

    def readchunk(self):
        if self.remote_file.closed:
            return None

        return self.remote_file.read(self.chunk_size)

    def download(self):
        b = io.BytesIO()
        chunk = self.readchunk()
        while chunk:
            b.write(chunk)
            chunk = self.readchunk()
        self.remote_file.seek(0)
        b.seek(0)

        return b


KLEIO_IS_ON = False
KLEIO_TRIAL_ID = os.getenv('KLEIO_TRIAL_ID', None)
KLEIO_VERBOSITY = int(os.getenv('KLEIO_VERBOSITY', 0))
trial = None
flatten = None
unflatten = None
if KLEIO_TRIAL_ID:
    KLEIO_IS_ON = True
    from kleio.core.io.trial_builder import TrialBuilder
    from kleio.core.evc.trial_node import TrialNode
    from kleio.core.utils import flatten, unflatten
    levels = {0: logging.WARNING,
              1: logging.INFO,
              2: logging.DEBUG}
    logging.basicConfig(level=levels.get(KLEIO_VERBOSITY, logging.DEBUG))
    python_logger.debug("Initiating database inside user script")
    TrialBuilder().build_database({})  # {'debug': KLEIO_DEBUG_MODE})
    python_logger.debug("Initiating kleio logger inside user script")
    kleio_logger = Logger()
    python_logger.debug("Trial {} loaded inside kleio logger".format(kleio_logger.trial.item.id))
    IS_ORION_ON = True
else:
    kleio_logger = BackupLogger()
    AnalyzeLogger = BackupLogger
