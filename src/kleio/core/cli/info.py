import argparse
import pprint

from kleio.core.cli.base import get_trial_from_short_id
from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.trial.base import Trial
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
    trial = TrialNode.view(get_trial_from_short_id(args, args.pop('id'))['_id'])
    print('\n'.join("{}: {}".format(timestamp, cmdline) for timestamp, cmdline in trial.commandlines))
    print("ID:", trial.id)
    pprint.pprint(trial.hosts)
    pprint.pprint(trial.configuration)
    pprint.pprint(trial.status)
    pprint.pprint(trial.versions)
    pprint.pprint(trial.refers)
