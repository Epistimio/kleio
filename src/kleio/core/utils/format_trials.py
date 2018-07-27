# -*- coding: utf-8 -*-
"""
:mod:`kleio.core.utils.format_trials` -- Utility functions for formatting data
==============================================================================

.. module:: format_trials
   :platform: Unix
   :synopsis: Conversion functions between various data types used in
      framework's ecosystem.

"""

from kleio.core.worker.trial import Trial


def trial_to_tuple(trial, space):
    """Extract a parameter tuple from a `kleio.core.worker.trial.Trial`.

    The order within the tuple is dictated by the defined
    `kleio.algo.space.Space` object.
    """
    assert len(trial.params) == len(space)
    for order, param in enumerate(trial.params):
        assert space[order].name == param.name
    return tuple([param.value for param in trial.params])


def tuple_to_trial(data, space):
    """Create a `kleio.core.worker.trial.Trial` object from `data`,
    filling only parameter information from `data`.

    :param data: A tuple representing a sample point from `space`.
    :param space: Definition of problem's domain.
    :type space: `kleio.algo.space.Space`
    """
    assert len(data) == len(space)
    params = []
    for i, dim in enumerate(space.values()):
        try:
            datum = data[i].tolist()  # if it is numpy.ndarray
        except AttributeError:
            datum = data[i]
        params.append(dict(
            name=dim.name,
            type=dim.type,
            value=datum
            ))
    return Trial(params=params)


def get_trial_results(trial):
    """Format results from a `Trial` using standard structures."""
    results = dict()
    obj = trial.objective
    results['objective'] = obj.value if obj else None
    results['constraint'] = [result.value for result in trial.results
                             if result.type == 'constraint']
    grad = trial.gradient
    results['gradient'] = tuple(grad.value) if grad else None

    return results


def standard_param_name(name):
    """Convert parameter name to namespace format"""
    return name.lstrip("/").lstrip("-").replace("-", "_")
