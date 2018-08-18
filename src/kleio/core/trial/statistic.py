from collections import defaultdict
import copy

from .attribute import event_based_diff, unfold_event_based_diff


class Statistics(object):
    def __init__(self, history, keys=None, sorted_by=tuple()):
        if isinstance(history, (list, tuple)):
            history = dict(zip(range(len(history)), history))
        self.history = history
        self._keys = keys

    def __getattr__(self, name):

        if self.history and isinstance(next(iter(self.history.values())), Statistics):
            raise RuntimeError("Cannot fetch statistics on statistics...")

        config = defaultdict(list)

        subdict_detected = False
        for i, event in enumerate(self.history.values()):
            if name in event or name in event['item']:
                event = copy.deepcopy(event)

                if name in event:
                    value = event.pop(name)
                if name in event['item']:
                    value = event['item'].pop(name)

                if isinstance(value, dict):
                    event['item'].update(value)
                    config[name].append(event)
                    subdict_detected = True
                else:
                    assert not subdict_detected
                    config[value].append(event)

        if subdict_detected:
            assert len(config) == 1
            statistics = Statistics(config[name])
        else:
            statistics = Statistics(dict((key, Statistics(history))
                                    for key, history in config.items()),
                                    keys=config.keys())
        return statistics

    def __getitem__(self, index):
        if self.keys is None:
            raise RuntimeError("No keys available at this level. "
                               "Fetch first from %s".format(self.attributes()))
        # if index not in
        return self.history[index]

    def to_dict(self):
        config = {}
        for key, event in self.history.items():
            if isinstance(event, Statistics):
                runtime_timestamp = min(event['runtime_timestamp']
                                        for event in event.history.values())
                event = dict(
                    runtime_timestamp=runtime_timestamp,
                    item=event.to_dict())

            if self._keys is None:
                prior = config
            else:
                prior = config.get(key, {})

            new_start_time = event['runtime_timestamp']
            diff = event_based_diff(None, new_start_time, prior, event['item'])

            if self._keys is None:
                config = diff
            else:
                config[key] = diff

        return unfold_event_based_diff(config)

    def keys(self):
        return self._keys  # self.history.keys()

    def items(self):
        return self.history.items()

    def attributes(self):
        attributes = set()
        for event in self.history.values():
            if isinstance(event, Statistics):
                attributes |= set(event.attributes())
            else:
                attributes |= set(event['item'].keys())

        return attributes

    def __str__(self):
        return "Statistics({})".format(", ".join(str(k) for k in sorted(self.attributes())[:10]))
