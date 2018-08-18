import argparse
import time

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    tail_parser = parser.add_parser('tail', help='tail help')

    tail_parser.add_argument(
        'id', help="id of the trial. Can be name or hash.")

    tail_parser.add_argument(
        '-f', '--follow', action='store_true',
        help="Follow the output of the script.")

    tail_parser.set_defaults(func=main)

    return tail_parser


def main(args):
    TrialBuilder().build_database(args)
    trial = TrialNode.view(args['id'])
    idx = max(len(trial.stdout) - 5, 0)
    print("\n".join(trial.stdout[idx:]))
    while args['follow'] and trial.status == "running":
        time.sleep(5)
        idx = len(trial.stdout)
        trial.update()
        new_lines = "\n".join(trial.stdout[idx:])
        if new_lines:
            print(new_lines)
