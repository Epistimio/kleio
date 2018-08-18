import argparse

from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.wrapper import Consumer


def add_default_subparser(parser, name):
    run_parser = parser.add_parser(name, help='run help')

    run_parser.add_argument(
        '--capture', action='store_true',
        help=('Capture log output of the executed script. '
              'By default it is printed in terminal.'))

    run_parser.add_argument(
        '--switch-over', action='store_true',
        help=('Execute trial even if broken.'))

    run_parser.add_argument(
        '--tags', default="",
        help=('Tag for the trial, separated with `;`'))

    run_parser.add_argument(
        'commandline', nargs=argparse.REMAINDER, metavar='...',
        help="Command line of user script. A configuration "
             "file intended to be used with 'userscript' must be given as a path "
             "in the **first positional** argument OR using `--config=<path>` "
             "keyword argument.")

    run_parser.set_defaults(func=default)

    return run_parser


def default(args):
    root_working_dir = args.pop('root_working_dir', '.')
    capture = args.pop('capture', False)
    tags = args.pop('tags', "")
    switchover = args.pop('switch_over', False)
    trial = TrialBuilder().build_from(args)
    if trial.status == 'broken' and switchover:
        trial.switchover()
    for tag in tags.split(";"):
        if tag not in trial._tags.get():
            trial._tags.append(tag)
        # trial.save()
    Consumer(root_working_dir, capture).consume(trial)
