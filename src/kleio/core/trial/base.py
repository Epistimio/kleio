# -*- coding: utf-8 -*-
# pylint: skip-file
"""
:mod:`kleio.core.worker.trial` -- Container class for `Trial` entity
=====================================================================

.. module:: trial
   :platform: Unix
   :synopsis: Describe a particular training run, parameters and results

"""
import copy
import datetime
import hashlib
import logging

from kleio.core.io.database import Database, ReadOnlyDB, DuplicateKeyError
from kleio.core.utils import sorteddict
from .attribute import (
    event_based_property, EventBasedAttribute,
    EventBasedListAttributeWithDB, EventBasedItemAttributeWithDB, EventBasedFileAttributeWithDB)
from .statistic import Statistics


log = logging.getLogger(__name__)


DEFAULT_PROJECT = "no_project"


# agglutinative: we want all of it
# stdout, stderr

# accumulative: we want some parts
# stats, artifacts, refs: accumulative

# single: we want a single status
# status, name, project


_NO_FIRST_ITEM = object()

COMMANDLINE_HASHING_ERROR = """
Commandline is used in hashing, so it should not be possible to load
a trial with a different commandline. Please report this error at
https://github.com/epistimio/kleio/issues with the following message.

hash:
{trial.hash_name}
Current commandline:
{trial.commandline}
Commandline from database:
{config[commandline]}
"""

CONFIGURATION_HASHING_ERROR = """
Configuration is used in hashing, so it should not be possible to load
a trial with a different configuration. Please report this error at
https://github.com/epistimio/kleio/issues with the following message.

hash:
{trial.hash_name}
Current configuration:
{trial.configuration}
Configuration from database:
{config[configuration]}
"""

# TODO: hashing is not anymore in configuration only
CONFIGURATION_CORRUPTION_ERROR = """
Current configuration hashing is different than the one saved in database.
This is likely to be caused by a corruption of the configuration as it would change the hashing.
Please report this error at https://github.com/epistimio/kleio/issues with the following message.

hash:
{trial.hash_name}
Current configuration:
{trial.configuration}
hash from database:
{config[_id]}
Configuration from database:
{config[configuration]}
"""


# commands: add, remove
# commands: set

# What if we query on status?
# What if we query on tags?
# What if we query on


# get name
# filter all events containing that name
# Build a new Statistics sorted according to this value
# backtrack, select from it
# backtrack, select from it


# self._tags.save(self.id)


# statistics
# artifacts
# ressources


# Status
# New -> reserved -> running -> broken -> switchover -> reserved
#                            -> failover -> reserved
#                            -> suspended -> reserved
#                            -> interrupted -> reserved
#                            -> completed

# Immutable
# config -> hash
# version
# host
#
# Mutable
# status

# Aggregating (but each stamp is immutable)
# stdout (use event sourcing rather than appending lines)
# stderr (use event sourcing rather than appending lines)
# statistics
# artifacts
# ressources


def create_event(item):
    if "_timestamp" in item:
        raise ValueError("You cannot use reserved attribute _timestamp.")

    item["_timestamp"] = datetime.datetime.utcnow()
    return item


class Trial(object):
    """Represents an entry in database/trials collection.

    Attributes
    ----------
    experiment : str
       Unique identifier for the experiment that produced this trial.
       Same as an `Experiment._id`.
    status : str
       Indicates how this trial is currently being used. Can take the following
       values:

       * 'new' : Denotes a fresh set of parameters suggested by an algorithm,
          not yet tried out.
       * 'reserved' : Indicates that this trial is currently being evaluated by
          a worker process, it was a 'new' trial that got selected.
       * 'completed' : is the status of a previously 'reserved' trial that
          successfully got evaluated. `Trial.results` must contain the evaluation.
       * 'interrupted' : Indicates trials that are stopped from being evaluated
          by external *actors* (e.g. cluster timeout, KeyboardInterrupt, killing
          of the worker process).
       * 'broken' : Indicates a trial that was not successfully evaluated for not
          expected reason.
    worker : str
       Corresponds to worker's unique id that handled this trial.
    submit_time : `datetime.datetime`
       When was this trial save?
    start_time : `datetime.datetime`
       When was this trial first reserved?
    end_time : `datetime.datetime`
       When was this trial interruped or terminated?
    duration : int
       How many seconds did this trial lasted? Note that (end_time - start_time) is not equal to
       duration if trial was interupted and resumed.
    configuration : dict
       Command line arguments of the trial and configuration file.
    statistics: dict of `Trial.Statistic`
       Dictionary of statistics reported for this particular trial.
    resources: list of `Trial.Resource`
       List of files openend within the trial.
    artifacts: list of `Trial.Artifact`
       List of files created within the trial.
    """

    @classmethod
    def build(cls, interval=(None, None), **kwargs):
        trial = cls(**kwargs)
        trial_from_db = cls.load(trial.id, interval=interval)
        if trial_from_db:
            return trial_from_db

        # This will raise DuplicateKeyError if there was any race condition
        trial.save()

        return trial

    @classmethod
    def load(cls, trial_id, interval=(None, None)):
        """Builder method for a list of trials.

        :param trial_entries: List of trial representation in dictionary form,
           as expected to be saved in a database.

        :returns: a list of corresponding `Trial` objects.
        """
        db = Database()
        config = db.read(cls.trial_immutable_collection, {'_id': trial_id})
        if not config:
            return None

        config[0].pop('_id')
        trial = cls(interval=interval, **config[0])
        trial._saved = True
        trial.update()  # Update the attributes

        return trial

    @classmethod
    def view(cls, trial_id, interval=(None, None)):
        """Builder method for a list of trials.

        :param trial_entries: List of trial representation in dictionary form,
           as expected to be saved in a database.

        :returns: a list of corresponding `Trial` objects.
        """
        trial = cls.load(trial_id, interval)
        if trial is None:
            return None

        return TrialView(trial)

    class Statistic(object):
        """Container for a value object.

        Attributes
        ----------
        name : str
           A possible named for the quality that this is quantifying.
        timestamp: float
           Duration time (in seconds) at which the statistic is reported within the trial.
        value : str or numerical
           value suggested for this dimension of the parameter space.

        """

        __slots__ = ('name', 'value')
        allowed_types = ()

        def __init__(self, **kwargs):
            """See attributes of `Value` for possible argument for `kwargs`."""
            for attrname in self.__slots__:
                setattr(self, attrname, None)
            for attrname, value in kwargs.items():
                setattr(self, attrname, value)

        def to_dict(self):
            """Needed to be able to convert `Value` to `dict` form."""
            ret = dict(
                name=self.name,
                value=self.value)
            return ret

        def __eq__(self, other):
            """Test equality based on self.to_dict()"""
            return self.name == other.name and self.value == other.value

        def __str__(self):
            """Represent partially with a string."""
            ret = "{0}(name={1}, value={3})".format(
                type(self).__name__, repr(self.name), repr(self.value))
            return ret

        __repr__ = __str__

    class Resource(object):
        pass

    class Artifact(object):
        pass

    # Fields
    #
    # version:
    #     type
    #     commit
    #     dirty
    #     diff

    # host:
    #     cpu
    #     gpu
    #     hostname
    #     username
    #     cluster if applicable
    #     O.S.
    #     ENV captured environment variables (if set)

    # stdout
    # stderr

    # status: [
    #         {name:
    #          timestamp:}
    #         ]

    # start_time = [first running status]['timestamp']
    # stop_time = [if last status is not reserved or running]['timestamp'] else None
    # duration sum(status after running - status running)
    # when cleaning, last running status is appended with failover with same timestamp, then
    # interupted with current timestamp

    # commandline
    # configuration file
    # comment

    # params: fetch from commandline and configuration file

    # log_artifact()
    # get_artifact() How to define indexes?

    __slots__ = ('_db', '_saved', '_status', '_refers',
                 '_tags', '_host', '_version', '_commandline', '_configuration',
                 '_stdout', '_stderr', '_interval', '_statistics', '_artifacts')
    # _hashable = ('host', 'version', 'configuration')
    _hashable = ('refers', 'host', 'version', 'commandline', 'configuration')
    allowed_stati = ('new', 'reserved', 'running', 'failover', 'switchover', 'suspended',
                     'completed', 'interrupted', 'broken')
    reservable_stati = ('new', 'suspended', 'interrupted', 'failover', 'switchover')
    interruptable_stati = ('running', )
    switchover_stati = ('reserved', 'broken')

    trial_immutable_collection = 'trials.immutables'
    trial_report_collection = 'trials.reports'

    def __init__(self, commandline, configuration, version, refers, host, interval=(None, None)):
        """See attributes of `Trial` for meaning and possible arguments for `kwargs`."""
        self._db = Database()
        self._saved = False
        # TODO: kleio.config.DEFAULT_PROJECT
        self._refers = sorteddict(refers)
        self._commandline = sorteddict(commandline)
        self._configuration = sorteddict(configuration)
        self._version = sorteddict(version)
        self._host = sorteddict(host)
        self._tags = EventBasedListAttributeWithDB(self.id, 'tags', interval)
        self._status = EventBasedItemAttributeWithDB(self.id, 'status', interval)
        self._stdout = EventBasedListAttributeWithDB(self.id, 'stdout', interval)
        self._stderr = EventBasedListAttributeWithDB(self.id, 'stderr', interval)
        self._statistics = EventBasedListAttributeWithDB(self.id, 'statistics', interval)
        self._artifacts = EventBasedFileAttributeWithDB(self.id, 'artifacts', interval)
        self._interval = interval

        # TODO: Add attribute _heartbeat frequency so that its saved in database and do not get
        # incoherent if current config changes, trials heartbeat frequency will be known
        # TODO: No need for that, we can infer frequency by looking at the frequency, only local
        # definition is required for running trial. Hum, what if there is only a single running
        # saved? We cannot infer? Then what?

    # Use immutable collection for race conditions on id registration
    # Use report collection for race conditions on status changes

    def _set_status(self, new_status, allowed_stati, invalid_status_message=None,
                    race_condition_message=None):

        status = self.status

        if invalid_status_message is None:
            invalid_status_message = ("Trial with status '{status}' cannot "
                                      "be set to '{new_status}'.")

        if race_condition_message is None:
            race_condition_message = ("Trial status changed meanwhile. "
                                      "Switch to '{new_status}' failed.")

        if status not in allowed_stati:
            raise RuntimeError(invalid_status_message.format(status=status, new_status=new_status))

        try:
            # If status changed from reserved meanwhile, than the id while could a duplicate key
            # error, making this that this fails if the status changed meanwhile.
            self.status = new_status
        except DuplicateKeyError as e:
            raise RuntimeError(
                race_condition_message.format(new_status=new_status)) from e

    def running(self):
        self._set_status('running', ['reserved'])

    def reserve(self):
        # TODO: If status is broken given commandline to restore
        self._set_status('reserved', self.reservable_stati)

    def switchover(self):
        self._set_status('switchover', self.switchover_stati)

    def heartbeat(self):
        self._set_status(
            'running', ['running'],
            "Trial with status '{status}' cannot have a heartbeat.",
            "Trial status changed meanwhile. Heartbeat failed.")

    def interupt(self):
        self._set_status('interrupted', self.interruptable_stati)

    def suspend(self):
        self._set_status('suspended', self.interruptable_stati)

    def complete(self):
        self._set_status('completed', ['running'])

    def broken(self):
        self._set_status('broken', ['running'])

    @event_based_property
    def stdout(self):
        # return sum([event['item'] for event in self._stdout], [])
        return self._stdout.get()

    @event_based_property
    def stderr(self):
        # return sum([event['item'] for event in self._stderr], [])
        return self._stderr.get()

    @stdout.incrementer
    def stdout(self, new_lines):
        self._stdout.append(new_lines)

    @stderr.incrementer
    def stderr(self, new_lines):
        self._stderr.append(new_lines)

    @event_based_property
    def tags(self):
        return self._tags.get()

    @tags.incrementer
    def tags(self, new_tags):
        for tag in new_tags:
            # if a tag is added meanwhile by another process this while key DuplicateKeyError
            if tag not in self._tags.get():
                self._tags.append(tag)

    @property
    def commandline(self):
        return " ".join(self._commandline) if self._commandline else ""

    # TODO
    # @property
    # def commandlines(self):
    #     if self._node.parent:
    #         commandlines = self._node.parent.item.commandlines
    #     else:
    #         commandlines = EventBasedItemAttribute()

    #     commandlines.set(self.commandline, timestamp=self._node.parent.branching_point)
    #     return commandlines

    @property
    def start_time(self):
        return self._status.history[0]['runtime_timestamp']

    @property
    def end_time(self):
        return self._status.history[-1]['runtime_timestamp']

    @property
    def configuration(self):
        # TODO: read from command line and configuration files
        # TODO: Move comment above into trial building or resolve_config
        # configuration = self._node.parent.item.configuration()
        # return append_configs(self._node.parent.branching_point, configuration,
        #                       self._configuration)
        return self._configuration

    def _load_from_db(self, _id=None):
        # TODO Move those assert tests elsewhere
        raise NotImplemented()
        config = self._db.read(self.trial_immutable_collection, {'_id': _id if _id else self.id})

        # Load from scratch
        if config:
            config = config[0]
            self._saved = True

            # Immutable
            if self._commandline is not None and config['commandline'] == self._commandline:
                raise BaseException(COMMANDLINE_HASHING_ERROR.format(trial=self, config=config))
            self._commandline = config['commandline']

            # assert (self._configuration is None or config['configuration'] == self._configuration,
            #         CONFIGURATION_HASHING_ERROR.format(trial=self, config=config))
            # self._configuration = config['configuration']

            # assert (self._version is None or config['version'] == self._version,
            #         VERSION_HASHING_ERROR.format(trial=self, config=config))
            # self._version = config['version']

            # assert (self._host is None or config['host'] == self._host,
            #         HOST_HASHING_ERROR.format(trial=self, config=config))
            # self._host = config['host']

            # assert (self._refers is None or config['refers'] == self._refers,
            #         REFERS_HASHING_ERROR.format(trial=self, config=config))
            # self._refers = config['refers']

            # assert (self.hash_name == config['_id'],
            #         CONFIGURATION_CORRUPTION_ERROR.format(trial=trial, config=config))

            # if host is different,
            #     then it should branch
            # if version is different,
            #     then it should branch

            # What about when initializing it?
            # We have version
            # We don't have host
            # But if we set set host, then hash will change
            #  -> At the upper level, detect if host is empty and add option --allow-host-change

            # Mutable categorization
            self._tags.load(self.id)
            self._name.load(self.id)

            # Mutable/evolving info
            self._status.load(self.id)
            self._stdout.load(self.id)
            self._stderr.load(self.id)

            # TODO: Statistics and others

    def update(self):
        # Mutable categorization
        self._tags.load()

        # Mutable/evolving info
        self._status.load()
        self._stdout.load()
        self._stderr.load()

        self._statistics.load()
        self._artifacts.load()

    def save(self):
        # TODO: detect if not new, then update.
        # This will raise DuplicateKeyError if a concurrent trial with
        # identical id is written first in the database.
        if not self._saved:
            self._save_immutable()
            self._saved = True

        self._save_report()

        return self

    @property
    def refers(self):
        if self._refers is None:
            return sorteddict({
                'parent_id': None,
                'runtime_timestamp': None
            })

        return copy.deepcopy(self._refers)

    def _save_immutable(self):
        if self._commandline is None or self._configuration is None:
            raise RuntimeError("Cannot save trial if commandline and configuration "
                               "are not set.")

        # Immutable
        trial_dict = {
            '_id': self.id,
            'refers': self.refers,
            'commandline': self._commandline,
            'configuration': self._configuration,
            'version': self.version,
            'host': self.host
        }

        # Save immutable to make sure _id is available
        self._db.write(self.trial_immutable_collection, trial_dict)

        # # Mutable categorization
        # self._tags.set_id(self.id)

        # # Mutable/evolving info
        # self._status.set_id(self.id)
        # self._stdout.set_id(self.id)
        # self._stderr.set_id(self.id)

        # self._save_report()

    def _save_report(self):

        query = {
            '_id': self.id
        }

        trial_dict = {
            # Immutable
            '_id': self.id,
            'refers': self.refers,
            'commandline': self._commandline,
            'configuration': self._configuration,
            'version': self.version,
            'host': self.host,

            # Mutable
            'tags': self.tags,
            'registry': {
                'status': self.status,
                'start_time': self.start_time,
            }
            # statisticts?
            # artifacts?
            # ressources?
        }

        self._db.write(self.trial_report_collection, trial_dict, query=query)

    # def to_dict(self):
    #     """Needed to be able to convert `Trial` to `dict` form."""
    #     trial_dictionary = dict()

    #     # Mutable categorization
    #     trial_dictionary['tags'] = self._tags.history
    #     trial_dictionary['name'] = self._name.history

    #     # Immutable
    #     trial_dictionary['commandline'] = self._commandline
    #     trial_dictionary['configuration'] = self._configuration
    #     trial_dictionary['version'] = self._version
    #     trial_dictionary['host'] = self._host

    #     # Mutable/evolving info
    #     trial_dictionary['status'] = self._status.history
    #     trial_dictionary['stdout'] = self._stdout.history
    #     trial_dictionary['stderr'] = self._stderr.history

    #     trial_dictionary['_id'] = self.id

    #     return trial_dictionary

    def __str__(self):
        """Represent partially with a string."""
        ret = "Trial(id={0}, status={1})".format(repr(self.id), repr(self.status))
        return ret

    __repr__ = __str__

    @property
    def status(self):
        """For meaning of property type, see `Trial.status`."""
        if not self._status.history:
            self.status = 'new'

        return self._status.get()

    @status.setter
    def status(self, status):
        if status is not None and status not in self.allowed_stati:
            raise ValueError("Given status, {0}, not one of: {1}".format(
                status, self.allowed_stati))

        self._status.set(status)

    @property
    def id(self):
        """Return hash_name which is also the database key `_id`."""
        # if self.name:
        #     return self.name

        return self.__hash__()

    @property
    def hash_name(self):
        """Generate a unique name with an md5sum hash for this `Trial`.

        .. note::

            Two trials that have the same `configuration` must have the same `hash_name`.

        .. note::

            If a trial is a branch, his hash_name is computed based on the composed configuration.
        """
        hash_string = "".join(str(getattr(self, name)) for name in self._hashable).encode('utf-8')
        return hashlib.md5(hash_string).hexdigest()

    def __hash__(self):
        """Return the hashname for this trial"""
        return self.hash_name

    @property
    def version(self):
        return copy.deepcopy(self._version)

    @property
    def host(self):
        return copy.deepcopy(self._host)

    @property
    def statistics(self):
        # statistics = {}
        # for event in self._statistics:
        #     for key in event['item'].keys():
        #         if key not in statistics:
        #             statistics[key] = {}

        #         statistics[key]
        return Statistics(self._statistics.history)

    def get_artifacts(self, filename, query):
        # statistics = {}
        # for event in self._statistics:
        #     for key in event['item'].keys():
        #         if key not in statistics:
        #             statistics[key] = {}

        #         statistics[key]
        return self._artifacts.get(filename, query)

    @property
    def resources(self):
        return []

    def add_statistic(self, timestamp=None, creator=None, **statistics):
        self._statistics.append(statistics, timestamp=timestamp, creator=creator)

    def add_artifact(self, filename, artifact, **attributes):
        self._artifacts.add(filename, artifact, attributes)

    def add_resource(self, name, value):
        pass


# pylint: disable=too-few-public-methods
class TrialView(object):
    """Non-writable view of an trial

    .. seealso::

        :py:class:`orion.core.worker.trial.Trial` for writable trials.

    """

    __slots__ = ('_trial', )

    #                   Attributes
    valid_attributes = ([] +
                        # Properties
                        ["id", "tags", "status", "refers", "host", "version", "commandline",
                         "configuration", "stdout", "stderr", "interval", "hash_name",
                         "start_time", "end_time", "statistics", "get_artifacts"] +
                        # Methods
                        ["update"])

    def __init__(self, trial):
        trial._db = ReadOnlyDB(trial._db)

        # Attributes as well
        for attrname in trial.__slots__:
            attr = getattr(trial, attrname)
            if isinstance(attr, EventBasedAttribute):
                attr._db = trial._db

        self._trial = trial

    def __getattr__(self, name):
        """Get attribute only if valid"""
        if name not in self.valid_attributes:
            raise AttributeError("Cannot access attribute %s on view-only trials." % name)

        return getattr(self._trial, name)

    def __str__(self):
        """Represent the object as a string."""
        return str(self._trial).replace("Trial", "TrialView")

    __repr__ = __str__
