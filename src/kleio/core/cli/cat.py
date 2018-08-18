import argparse

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    cat_parser = parser.add_parser('cat', help='cat help')

    cat_parser.add_argument(
        'id', help="id of the trial. Can be name or hash.")

    cat_parser.add_argument(
        '--stderr', action="store_true", help="Print the stderr as well.")

    cat_parser.set_defaults(func=main)

    return cat_parser


def main(args):
    TrialBuilder().build_database(args)
    trial = TrialNode.view(args['id'])
    print('\n'.join(trial.stdout))

    if args.get('stderr'):
        print()
        print('\n'.join(trial.stderr))
