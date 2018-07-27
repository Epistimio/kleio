# -*- coding: utf-8 -*-
# pylint: skip-file
"""
:mod:`kleio.core.worker.trial` -- Container class for `Trial` entity
=====================================================================

.. module:: trial
   :platform: Unix
   :synopsis: Describe a particular training run, parameters and results

"""
import hashlib
import logging

log = logging.getLogger(__name__)


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
    def build(cls, trial_entries):
        """Builder method for a list of trials.

        :param trial_entries: List of trial representation in dictionary form,
           as expected to be saved in a database.

        :returns: a list of corresponding `Trial` objects.
        """
        trials = []
        for entry in trial_entries:
            trials.append(cls(**entry))
        return trials

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
                value=self.value
                )
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
    # VCS:
    #     type
    #     commit
    #     dirty
    #     diff

    # host:
    #     cpu
    #     gpu
    #     hostname
    #     cluster if applicable
    #     O.S.
    #     ENV captured environment variables (if set)

    # stdout
    # stderr

    # start_time
    # stop_time
    # duration (because there may be multiple stop times)
    # heartbeat_time
    # status

    # commandline
    # configuration file
    # comment

    # params: fetch from commandline and configuration file

    __slots__ = ('experiment', '_status', 'worker',
                 'submit_time', 'start_time', 'end_time', 'results', 'params')
    allowed_stati = ('new', 'reserved', 'suspended', 'completed', 'interrupted', 'broken')

    def __init__(self, **kwargs):
        """See attributes of `Trial` for meaning and possible arguments for `kwargs`."""
        for attrname in self.__slots__:
            if attrname in ('results', 'params'):
                setattr(self, attrname, list())
            else:
                setattr(self, attrname, None)

        self.status = 'new'

        # Remove useless item
        kwargs.pop('_id', None)

        for attrname, value in kwargs.items():
            if attrname == 'results':
                attr = getattr(self, attrname)
                for item in value:
                    attr.append(self.Result(**item))
            elif attrname == 'params':
                attr = getattr(self, attrname)
                for item in value:
                    attr.append(self.Param(**item))
            else:
                setattr(self, attrname, value)

    def to_dict(self):
        """Needed to be able to convert `Trial` to `dict` form."""
        trial_dictionary = dict()

        for attrname in self.__slots__:

            attrname = attrname.lstrip("_")
            trial_dictionary[attrname] = getattr(self, attrname)

        # Overwrite "results" and "params" with list of dictionaries rather
        # than list of Value objects
        for attrname in ('results', 'params'):
            trial_dictionary[attrname] = list(map(lambda x: x.to_dict(),
                                                  getattr(self, attrname)))

        trial_dictionary['_id'] = self.id

        return trial_dictionary

    def __str__(self):
        """Represent partially with a string."""
        ret = "Trial(experiment={0}, status={1},\n      params={2})".format(
            repr(self.experiment), repr(self._status), self.params_repr(sep=('\n' + ' ' * 13)))
        return ret

    __repr__ = __str__

    @property
    def status(self):
        """For meaning of property type, see `Trial.status`."""
        return self._status

    @status.setter
    def status(self, status):
        if status is not None and status not in self.allowed_stati:
            raise ValueError("Given status, {0}, not one of: {1}".format(
                status, self.allowed_stati))
        self._status = status

    @property
    def id(self):
        """Return hash_name which is also the database key `_id`."""
        return self.__hash__()

    @property
    def statistics(self):
        return []

    @property
    def resources(self):
        return []

    @property
    def artifacts(self):
        return []

    def add_statistic(self, name, value):
        pass

    def add_resource(self, name, value):
        pass

    def add_artifact(self, name, value):
        pass
