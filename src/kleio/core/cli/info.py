import argparse
import pprint

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    info_parser = parser.add_parser('info', help='info help')

    info_parser.add_argument(
        'id', help="id of the trial. Can be name or hash.")

    info_parser.add_argument(
        '-f', '--follow', action='store_true',
        help="Follow the output of the script.")

    info_parser.set_defaults(func=main)

    return info_parser


def main(args):
    TrialBuilder().build_database(args)
    trial = TrialNode.load(args['id'])
    print('\n'.join("{}: {}".format(timestamp, cmdline) for timestamp, cmdline in trial.commandlines))
    pprint.pprint(trial.host)
    pprint.pprint(trial.configuration)
    pprint.pprint(trial.status)
    pprint.pprint(trial.version)
    pprint.pprint(trial.refers)
