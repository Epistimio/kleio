import argparse

from kleio.core.cli.base import get_trial_from_short_id
import kleio.core.cli.base as cli
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

    cli.get_version_args_group(exec_parser)

    exec_parser.set_defaults(func=main)

    return exec_parser


def main(args):
    root_working_dir = args.pop('root_working_dir', '.')
    capture = args.pop('capture', False)
    debug = args.get('debug', False)
    args['id'] = get_trial_from_short_id(args, args.pop('id'))['_id']
    trial = TrialBuilder().build_from_id(args)
    try:
        Consumer(root_working_dir, capture, debug).consume(trial)
    except KeyboardInterrupt as e:
        raise SystemExit()
