import argparse
import time

from kleio.core.cli.base import get_trial_from_short_id
from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    switchover_parser = parser.add_parser('switchover', help='switchover help')

    switchover_parser.add_argument(
        'ids', nargs='+', help="id[s] of the trial.")

    switchover_parser.set_defaults(func=main)

    return switchover_parser


def main(args):
    TrialBuilder().build_database(args)
    for trial_id in args.pop('ids'):
        trial = TrialNode.load(get_trial_from_short_id(args, trial_id)['_id'])
        try:
            trial.switchover()
        except RuntimeError as e:
            print("ERROR:{trial.short_id}: {err}".format(trial=trial, err=str(e)))
            continue
        trial.save()
        print("Trial {trial.short_id} status turned to switchover".format(trial=trial))
