import argparse
import time

from kleio.core.cli.base import get_trial_from_short_id
from kleio.core.trial.base import Trial
from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


SUSPENSION_FAILED = """
Error: Trial {trial.short_id} stopped for another reason and now has status '{trial.status}'

tail stdout:
{stdout}

tail stderr:
{stderr}

For a complete log of the trial use command
$ kleio cat {trial.short_id}
"""


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    suspend_parser = parser.add_parser('suspend', help='suspend help')

    suspend_parser.add_argument(
        'id', help="id of the trial. Can be name or hash.")

    suspend_parser.set_defaults(func=main)

    return suspend_parser


def main(args):
    database = TrialBuilder().build_database(args)
    trial = TrialNode.load(get_trial_from_short_id(args, args.pop('id'))['_id'])

    requested = False
    while not requested:
        try:
            trial.suspend()
            requested = True
        except RuntimeError as e:
            if "Trial status changed meanwhile." not in str(e):
                raise

            trial.update()

    trial.save()
    print("Request to suspend Trial {trial.short_id} has been registered".format(trial=trial))
    print("Waiting for confirmation...")

    suspended = False
    while not suspended:
        document = database.read(Trial.trial_report_collection, {'_id': trial.id}, {'registry.status': 1})[0]
        suspended = document['registry']['status'] == "suspended"

        if not suspended and document['registry']['status'] not in status.INTERRUPTABLE:
            print(SUSPENSION_FAILED.format(
                trial=trial, stdout=trial.stdout[-10:], stderr=trial.stderr[-10:]))

    print("Trial {trial.short_id} suspended successfully".format(trial=trial))
