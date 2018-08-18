import argparse
import sys
from pprint import pprint

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.trial.base import Trial
from kleio.core.evc.trial_node import TrialNode
from kleio.core.wrapper import Consumer


def add_subparser(parser):
    """Return the parser that needs to be used for this command"""
    pdb_parser = parser.add_parser('pdb', help='pdb help')

    pdb_parser.add_argument(
        'id', help="id of the trial. Can be name or hash.")

    pdb_parser.set_defaults(func=main)

    return pdb_parser


def main(args):
    database = TrialBuilder().build_database(args)
    trials = database.read(Trial.trial_immutable_collection, { '_id':  {'$regex' : '^{}'.format(args['id']) }})
    if len(trials) > 1:
        print("Select one of these ids")
        for trial in trials:
            print(trial['_id'])
        sys.exit(0)

    trial = TrialNode.view(trials[0]['_id'])
    import pdb
    pdb.set_trace()
