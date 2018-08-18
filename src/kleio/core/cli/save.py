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

    cli.get_basic_args_group(save_parser)

    # evc_cli.get_branching_args_group(save_parser)

    cli.get_user_args_group(save_parser)

    save_parser.set_defaults(func=main)

    return save_parser


def main(args):
    """Build and initialize experiment"""
    # By building the trial, we create a new trial document in database
    TrialBuilder().build_from(args)
