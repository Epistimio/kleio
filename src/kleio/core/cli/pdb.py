import argparse
import sys
from pprint import pprint

from kleio.core.cli.base import get_trial_from_short_id
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
    trial = TrialNode.view(get_trial_from_short_id(args, args.pop('id'))['_id'])
    import pdb
    pdb.set_trace()
