#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`kleio.core.cli.save` -- Module running the save command
==============================================================

.. module:: save
   :platform: Unix
   :synopsis: Creates a new trial.
"""

import logging

from kleio.core.cli import base as cli
# from kleio.core.cli import evc as evc_cli
from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode

log = logging.getLogger(__name__)


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    save_parser = parser.add_parser('save', help='save help')

    save_parser.add_argument(
        '--tags', default="",
        help=('Tag for the trial, separated with `;`'))

    save_parser.add_argument(
        '--branch-original', action="store_true",
        help=('If an identical trial is already registered, branch it from the beginning'
              'to start a new one.'))

    cli.get_basic_args_group(save_parser)

    # evc_cli.get_branching_args_group(save_parser)

    cli.get_user_args_group(save_parser)

    save_parser.set_defaults(func=main)

    return save_parser


def branch_leaf(trial, **config):
    try:
        trial = TrialNode.branch(trial.id, timestamp=trial.start_time, **config)
    except RuntimeError as e:
        if not "Branch already exist with id" in str(e):
            raise

        trial = branch_leaf(TrialNode.load(str(e).split(" ")[-1].strip("'")), **config)

    return trial


def main(args):
    """Build and initialize experiment"""
    # By building the trial, we create a new trial document in database
    trial_builder = TrialBuilder()
    tags = [tag for tag in args.pop('tags', "").split(";") if tag]

    if not args['commandline']:
        raise SystemExit("Cannot save an empty execution")

    branch_original = args.pop("branch_original", False)

    trial = trial_builder.build_view_from(args)

    if trial is not None and branch_original:
        if not tags:
            raise SystemExit("ERROR: You should not branch without giving any tags,"
                             "otherwise it is impossible to distinguish trials.")

        config = trial_builder.fetch_full_config(args)
        trial_builder._clean_config(config)
        # trial = TrialNode.branch(trial.id, timestamp=trial.start_time, **config)
        trial = branch_leaf(trial, **config)
    elif trial is not None:
        raise SystemExit("ERROR: Trial already registered with id: {}".format(trial.short_id))
    else:
        trial = trial_builder.build_from(args)

    for tag in tags:
        if tag not in trial._tags.get():
            trial._tags.append(tag)

    trial.save()
    print("Trial successfully registered with id: {}".format(trial.short_id))
