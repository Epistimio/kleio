import argparse
import sys

from kleio.core.io.database import DuplicateKeyError
from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


DUPLICATE_ERROR_MESSAGE = """
ERROR: Branch already exist with id '{trial.id}'.

Use the following command to continue executing it.
$ kleio exec {trial.id}

Or you can look at the details of the trial with
$ kleio info {trial.id}
"""


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    branch_parser = parser.add_parser('branch', help='branch help')

    branch_parser.set_defaults(func=main)

    branch_parser.add_argument(
        '--capture', action='store_true',
        help=('Capture log output of the executed script. '
              'By default it is printed in terminal.'))

    branch_parser.add_argument(
        'id', help="id of the trial. Can be hash or unique tag.")

    branch_parser.add_argument(
        '--tags', default="",
        help=('Tag for the trial, separated with `;`'))

    # TODO: int? datetime? some specific artifact like epochs?
    branch_parser.add_argument(
        '--timestamp', help="Time at which the trial will be branched. Default is end of trial.")

    # TODO: Support --config
    branch_parser.add_argument(
        'commandline', nargs=argparse.REMAINDER, metavar='...',
        help="New arguments to be used in the branch. A configuration "
             "file intended to be used with 'userscript' must be given "
             "using `--config=<path>` keyword argument.")

    return branch_parser


def main(args):
    root_working_dir = args.pop('root_working_dir', '.')
    capture = args.pop('capture', False)
    tags = args.pop('tags', "")

    TrialBuilder().build_database(args)
    config = TrialBuilder().fetch_full_config(args)

    config.pop('database', None)
    config.pop('resources', None)
    config.pop('debug', None)
    config.pop('id', None)

    try:
        trial = TrialNode.branch(args['id'], **config)
    except RuntimeError as e:
        if "Branch already exist with id" in str(e):
            raise

        raise SystemExit(DUPLICATE_ERROR_MESSAGE.format(trial=trial))

    for tag in tags.split(";"):
        if not tag:
            continue

        if tag not in trial._tags.get():
            trial._tags.append(tag)

    print("Note that branched trials may only be resumed using their id")

    Consumer(root_working_dir, capture).consume(trial)
