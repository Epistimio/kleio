from collections import defaultdict
import argparse
import datetime
import pprint

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.trial import status
from kleio.core.trial.attribute import EventBasedItemAttributeWithDB
from kleio.core.trial.base import Trial
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    cure_parser = parser.add_parser('cure', help='cure help')

    cure_parser.add_argument(
        '--tags', default="",
        help=('Tags for the trials, separated with `;`'))

    cure_parser.add_argument(
        '--extensive', action="store_true",
        help=('Test every single trials, not based on reports.'))

    cure_parser.add_argument(
        '--threshold-coefficient', default=10, type=float,
        help=('Trials are considered dead if last heartbeat is older than '
              'threshold-coefficient times the hearthbeat rate'))

    cure_parser.add_argument(
        '--print-only', action='store_true',
        help=('Only prints the action that would be taken, but execute nothing.'))

    cure_parser.set_defaults(func=main)

    return cure_parser


template = """\
{short_id}{status:<11} {commandline}\
"""

STATUS = [
    'new', 'reserved', 'running', 'completed',
    'suspended', 'interrupted', 'switchover', 'failover',
    'broken', 'branched']
 

def failover(trial_id, status, timestamp, threshold_coefficient, trial=None, print_only=False):
    # TODO: Get rid of magical number (10). It should be a config in kleio.
    heartbeat_rate = 10
    threshold = heartbeat_rate * threshold_coefficient
    if status == 'running' and (datetime.datetime.utcnow() - timestamp).seconds > threshold:
        if print_only:
            print("Turning {} to failover".format(trial_id[:7]))
            return

        if trial is None:
            trial = Trial.load(trial_id)

        if trial is None:
            print("ERROR: Trial {} not found".format(trial_id[:7]))
            return

        trial.failover()
        trial.save()
        return True

    return False


def get_reports(database, query):
    selection = {
        '_id': 1,
        'tags': 1,
        'registry.status': 1,
        'registry.end_time': 1
        }

    return {trial['_id']: trial
            for trial in  database.read(Trial.trial_report_collection, query, selection)}


beginning_of_time = datetime.datetime(1900, 1, 1)


def quick_cure(database, query, args):
    query['registry.status'] = {'$eq': 'running'}

    for trial_id, trial_doc in get_reports(database, query).items():
        end_time = trial_doc['registry'].get('end_time', beginning_of_time)
        failover(trial_id, 'running', end_time, args['threshold_coefficient'],
                 print_only=args['print_only'])


def extensive_cure(database, query, args):

    selection = {
        '_id': 1,
        }

    reports = get_reports(database, query)

    for trial_doc in database.read(Trial.trial_report_collection, query, selection):
        # TODO: Get rid of magical number (10). It should be a config in kleio.
        trial = Trial.load(trial_doc['_id'])
        trial._status.load()
        last_event = trial._status.history[-1]
        if not failover(trial.id, last_event['item'], last_event['runtime_timestamp'],
                        args['threshold_coefficient'], trial=trial, print_only=args['print_only']):
            if reports[trial.id]['registry'].get('end_time', beginning_of_time) < trial.end_time:
                print("Updating {trial.short_id} report".format(trial=trial))
                trial.update()
                trial.save()


def main(args):
    database = TrialBuilder().build_database(args)
    tags = [tag for tag in args.pop('tags', "").split(";") if tag]

    query = {
        'tags': {'$all': tags},
        }

    if not tags:
        query.pop('tags')

    if args['extensive']:
        extensive_cure(database, query, args)
    else:
        quick_cure(database, query, args)
