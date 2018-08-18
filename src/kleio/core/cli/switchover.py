import argparse
import time

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    switchover_parser = parser.add_parser('switchover', help='switchover help')

    switchover_parser.add_argument(
        'id', help="id of the trial. Can be name or hash.")

    switchover_parser.set_defaults(func=main)

    return switchover_parser


def main(args):
    TrialBuilder().build_database(args)
    trial = TrialNode.load(args['id'])
    trial.switchover()
