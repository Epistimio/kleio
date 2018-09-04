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

log = logging.getLogger(__name__)


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    save_parser = parser.add_parser('save', help='save help')

    save_parser.add_argument(
        '--tags', default="",
        help=('Tag for the trial, separated with `;`'))

    cli.get_basic_args_group(save_parser)

    # evc_cli.get_branching_args_group(save_parser)

    cli.get_user_args_group(save_parser)

    save_parser.set_defaults(func=main)

    return save_parser


def main(args):
    """Build and initialize experiment"""
    # By building the trial, we create a new trial document in database
    tags = [tag for tag in args.pop('tags', "").split(";") if tag]

    if not args['commandline']:
        raise SystemExit("Cannot save an empty execution")

    trial = TrialBuilder().build_view_from(args)

    if trial is not None:
        raise SystemExit("ERROR: Trial already registered with id: {}".format(trial.short_id))

    trial = TrialBuilder().build_from(args)

    for tag in tags:
        if tag not in trial._tags.get():
            trial._tags.append(tag)

    trial.save()
    print("Trial successfully registered with id: {}".format(trial.short_id))
