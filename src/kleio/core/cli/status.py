from collections import defaultdict
import argparse
import pprint

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.trial import status
from kleio.core.trial.base import Trial
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    status_parser = parser.add_parser('status', help='status help')

    status_parser.add_argument(
        '--tags', default="",
        help=('Tags for the trials, separated with `;`'))

    status_parser.set_defaults(func=main)

    return status_parser


template = """\
{short_id}{status:<11} {commandline}\
"""

STATUS = [
    'new', 'reserved', 'running', 'completed',
    'suspended', 'interrupted', 'switchover', 'failover',
    'broken', 'branched']
 

def print_group(group, results):
    print("\n# {} #\n".format(";".join(group) if group is not None else "total"))
    for status in STATUS:
        if status in results[group]:
            print("  {status:>15}: {number:5d}".format(
                status=status, number=results[group][status]))

def main(args):
    database = TrialBuilder().build_database(args)
    tags = [tag for tag in args.pop('tags', "").split(";") if tag]

    query = {
        'tags': {'$all': tags}
        }

    if not tags:
        query.pop('tags')

    selection = {
        '_id': 1,
        'tags': 1,
        'registry.status': 1
        }

    results = defaultdict(lambda : defaultdict(int))

    for trial in database.read(Trial.trial_report_collection, query, selection):
        results[None][trial['registry']['status']] += 1
        results[tuple(sorted(trial['tags']))][trial['registry']['status']] += 1

    if len(results.keys()) > 2:
        print_group(None, results)

    results.pop(None, None)

    for group in sorted(results.keys()):
        print_group(group, results)
