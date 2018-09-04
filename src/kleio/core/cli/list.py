import argparse
import pprint

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.trial import status
from kleio.core.trial.base import Trial
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    list_parser = parser.add_parser('list', help='list help')

    list_parser.add_argument(
        '--tags', default="",
        help=('Tag for the trial, separated with `;`'))

    list_parser.set_defaults(func=main)

    return list_parser


template = """\
{short_id}{status:<11} {commandline}\
"""


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
        'commandline': 1,
        'registry.status': 1
        }

    for trial in database.read(Trial.trial_report_collection, query, selection):
        line = template.format(
            short_id=trial['_id'][:7],
            status="[{}]".format(trial['registry']['status']),
            commandline=" ".join(trial['commandline']))

        print(line)
