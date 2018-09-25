import copy
import datetime

from kleio.core.io.database import Database
from kleio.core.utils import flatten, unflatten


class event_based_property(property):
    def __init__(self, fget=None, fset=None, fdel=None, iadd=None, doc=None):
        super(event_based_property, self).__init__(fget, fset, fdel, doc)
        self.iadd = iadd

    def __iadd__(self, obj, value):
        if self.iadd is None:
            raise AttributeError("can't iadd attribute")
        self.iadd(obj, value)

    def getter(self, fget):
        return type(self)(fget, self.fset, self.iadd, self.fdel, self.__doc__)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.iadd, self.fdel, self.__doc__)

    def incrementer(self, iadd):
        return type(self)(self.fget, self.fset, iadd, self.fdel, self.__doc__)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, self.iadd, fdel, self.__doc__)


def event_based_diff(old_start_time, new_start_time, old_config, new_config):
    old_config = flatten(old_config)

    for key, new_item in flatten(new_config).items():

        # New key, item
        if key not in old_config:
            old_config[key] = EventBasedItemAttribute()

        prior_item = old_config[key]
        if prior_item == new_item:
            continue

        # Turn attribute into event based and add prior and new items
        if not isinstance(prior_item, EventBasedItemAttribute):
            attr = EventBasedItemAttribute()
            attr.set(prior_item, timestamp=old_start_time)
            old_config[key] = attr

        old_config[key].set(new_item, timestamp=new_start_time)

    # TODO: Test that flatten/unflatten will do so in list of dicts as well.
    return unflatten(old_config)


def unfold_event_based_diff(diff):
    unfolded_diff = dict()
    for key, value in list(diff.items()):
        if isinstance(value, dict):
            value = unfold_event_based_diff(value)
        elif isinstance(value, EventBasedItemAttribute) and len(value.history) > 0:
            value = value.history[0]['item']

        unfolded_diff[key] = value

    return unfolded_diff


class EventBasedAttribute(object):
    def __init__(self):
        self.history = []

    def __iter__(self):
        return iter(self.history)

    def __getitem__(self, key):
        return self.history[key]

    def replay(self):
        raise NotImplemented()

    def get(self):
        return self.replay()

    def register_event(self, event_type, item, timestamp=None, creator=None):
        event = self.create_event(event_type, item, timestamp=timestamp, creator=creator)
        self.history.append(event)

    @classmethod
    def create_event(cls, event_type, item, timestamp=None, creator=None):
        creation_timestamp = datetime.datetime.utcnow()
        runtime_timestamp = timestamp if timestamp else creation_timestamp

        if not isinstance(runtime_timestamp, datetime.datetime):
            raise TypeError(
                "Timestamp must be of type datetime.datetime, not '{}'".format(
                    type(runtime_timestamp)))

        event = {
            'item': item,
            'type': event_type,
            'creation_timestamp': creation_timestamp,
            'runtime_timestamp': runtime_timestamp
        }

        return event


class EventBasedAttributeWithDB(EventBasedAttribute):
    """
    {
        _id:
        creation_timestamp:
        runtime_timestamp:
        trial_id:
        creator_id:
        item:{
        }
    }
    """
    indexes_built = set()

    def __init__(self, trial_id, name, interval=(None, None)):
        # NOTE: If interval is defined, than the attribute cannot write any new event
        # unless the interval covers all the events in the db. Interval is used for viewonly trials
        super(EventBasedAttributeWithDB, self).__init__()
        self._trial_id = trial_id
        self.name = name
        self._interval = interval
        self._db = Database()
        self._setup_db()

    def _setup_db(self):
        if self.collection_name not in EventBasedAttributeWithDB.indexes_built:
            try:
                self._db.ensure_index(self.collection_name, 'trial_id')
                self._db.ensure_index(self.collection_name, 'runtime_timestamp')
                self._db.ensure_index(self.collection_name, 'creation_timestamp')
            except BaseException as e:
                if not "not authorized on" in str(e):
                    raise

            EventBasedAttributeWithDB.indexes_built.add(self.collection_name)

    @property
    def collection_name(self):
        return "{}".format(self.name)

    @property
    def last_id(self):
        if not self.history:
            return 0

        return int(self.history[-1]['_id'].split(".")[-1])

    def load(self):
        query = {"trial_id": self._trial_id}
        lower_bound, upper_bound = self._interval
        if (self.history and
                (lower_bound is None or lower_bound < self.history[-1]['runtime_timestamp'])):
            lower_bound = self.history[-1]['runtime_timestamp']

        # Can't query anything anymore
        if lower_bound and upper_bound and lower_bound > upper_bound:
            return {}

        if lower_bound:
            query['runtime_timestamp'] = {'$gte': lower_bound}
        elif upper_bound:
            query['runtime_timestamp'] = {'$lte': upper_bound}

        new_events = self._db.read(self.collection_name, query)

        if self._interval[0] and self._interval[1]:
            new_events = [event for event
                          in new_events if event['runtime_timestamp'] <= upper_bound]

        self.history += self._filter_duplicates(new_events)

        return self

    def _filter_duplicates(self, new_events):
        if not self.history:
            return new_events

        last_id = self.last_id

        return [e for e in new_events if int(e['_id'].split(".")[-1]) > last_id]

    def _save(self, event):
        # Make sure we have full history
        event['_id'] = "{}.{}".format(self._trial_id, self.last_id + 1)
        self._db.write(self.collection_name, event)

    def register_event(self, event_type, item, timestamp=None, creator=None):
        event = self.create_event(event_type, item, timestamp=timestamp, creator=creator)
        event['trial_id'] = self._trial_id
        event['creator_id'] = creator if creator else self._trial_id
        self._save(event)
        self.history.append(event)


class EventBasedListAttribute(EventBasedAttribute):
    ADD = "add"
    REMOVE = "remove"

    def replay(self):
        items = []
        for event in self.history:
            if event['type'] == self.ADD:
                items.append(event['item'])
            elif event['type'] == self.REMOVE:
                del items[items.find(event['item'])]
            else:
                raise ValueError(
                    "Invalid event type '{}', must be '{}' or '{}'".format(
                        (event['type'], self.ADD, self.REMOVE)))

        return items

    def append(self, new_item, timestamp=None, creator=None):
        self.register_event(self.ADD, new_item, timestamp=timestamp, creator=creator)

    def remove(self, item, timestamp=None, creator=None):
        if item not in self.replay():
            raise RuntimeError(
                "Cannot remove item that is not in the list:\n{}".format(item))

        self.register_event(self.REMOVE, item, timestamp=timestamp, creator=creator)


class EventBasedListAttributeWithDB(EventBasedListAttribute, EventBasedAttributeWithDB):
    pass


class EventBasedFileAttributeWithDB(EventBasedAttributeWithDB):
    ADD = "add"
    db_is_setup = False

    def _setup_db(self):
        if self.collection_name not in EventBasedAttributeWithDB.indexes_built:
            try:
                self._db.ensure_index(self.collection_name + ".metadata", 'trial_id')
                self._db.ensure_index(self.collection_name + ".metadata", 'filename')
                self._db.ensure_index(self.collection_name + ".metadata", 'runtime_timestamp')
                self._db.ensure_index(self.collection_name + ".metadata", 'creation_timestamp')
            except BaseException as e:
                if not "not authorized on" in str(e):
                    raise

            EventBasedAttributeWithDB.indexes_built.add(self.collection_name)

    def replay(self):
        items = []
        for event in self.history:
            if event['type'] == self.ADD:
                items.append(event['item'])
            elif event['type'] == self.REMOVE:
                del items[items.find(event['item'])]
            else:
                raise ValueError(
                    "Invalid event type '{}', must be '{}' or '{}'".format(
                        (event['type'], self.ADD, self.REMOVE)))

        return items

    def register_event(self, event_type, item, timestamp=None, creator=None):
        file_like_object = item.pop('file_like_object')
        event = self.create_event(event_type, item, timestamp=timestamp, creator=creator)
        event['trial_id'] = self._trial_id
        self._save(event, file_like_object)
        self.history.append(event)

    def _save(self, event, file_like_object):
        # Make sure we have full history
        event['_id'] = "{}.{}".format(self._trial_id, self.last_id + 1)
        metadata = copy.deepcopy(event['item'])
        event.pop('item')
        metadata.update(event)
        file_id = self._db.write_file(self.collection_name, file_like_object, metadata=metadata)
        event['item'] = metadata
        event['item']['file_id'] = file_id
        self._db.write(self.collection_name, event)

    def add(self, filename, file_like_object, attributes, timestamp=None, creator=None):
        attributes['filename'] = filename
        attributes['file_like_object'] = file_like_object
        self.register_event(self.ADD, attributes, timestamp=timestamp, creator=creator)

    def get(self, filename, query):
        query = copy.deepcopy(query)
        query['trial_id'] = self._trial_id
        lower_bound, upper_bound = self._interval

        if lower_bound:
            query['runtime_timestamp'] = {'$gte': lower_bound}
        elif upper_bound:
            query['runtime_timestamp'] = {'$lte': upper_bound}

        query['filename'] = filename

        files = self._db.read_file(self.collection_name, query)

        if lower_bound and upper_bound:
            files = [f for f, metadata in files if metadata['runtime_timestamp'] <= upper_bound]

        return files


class EventBasedItemAttribute(EventBasedAttribute):
    SET = "set"

    def replay(self):
        return self.history[-1]['item']

    def set(self, new_item, timestamp=None, creator=None):
        self.register_event(self.SET, new_item, timestamp=timestamp, creator=creator)


class EventBasedItemAttributeWithDB(EventBasedItemAttribute, EventBasedAttributeWithDB):
    pass
