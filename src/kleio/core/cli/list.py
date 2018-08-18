import argparse
import pprint

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.trial.base import Trial
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    list_parser = parser.add_parser('list', help='list help')

    list_parser.set_defaults(func=main)

    return list_parser


def main(args):
    database = TrialBuilder().build_database(args)
    for trial in database.read(Trial.trial_immutable_collection, {}, {'_id': 1, 'commandline': 1}):
        print(trial['_id'], ": ", " ".join(trial['commandline']), sep="")
