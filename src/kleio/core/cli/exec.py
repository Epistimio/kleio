import argparse

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    exec_parser = parser.add_parser('exec', help='exec help')

    exec_parser.add_argument(
        '--capture', action='store_true',
        help=('Capture log output of the executed script. '
              'By default it is printed in terminal.'))

    exec_parser.add_argument(
        'id', help="id of the trial. Can be name or hash.")

    exec_parser.set_defaults(func=main)

    return exec_parser


def main(args):
    root_working_dir = args.pop('root_working_dir', '.')
    capture = args.pop('capture', False)

    TrialBuilder().build_database(args)

    trial = TrialNode.load(args['id'])
    Consumer(root_working_dir, capture).consume(trial)
