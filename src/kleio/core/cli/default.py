import argparse
import pprint
import traceback

from kleio.core.cli import base as cli
from kleio.core.io.database import Database
from kleio.core.io.trial_builder import TrialBuilder
from kleio.core.wrapper import Consumer
from kleio.core.trial import status
from kleio.core.trial.base import Trial
from kleio.core.evc.trial_node import TrialNode
from kleio.core.utils.diff import colored_diff


def add_default_subparser(parser, name):
    run_parser = parser.add_parser(name, help='run help')

    run_parser.add_argument(
        '--config', type=argparse.FileType('r'),
        help=('Configuration file for Kleio'))

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

    cli.get_version_args_group(run_parser)
    cli.get_user_args_group(run_parser)

    run_parser.set_defaults(func=default)

    return run_parser


def sequential_worker(consumer, args):
    allow_any_change = args.pop('allow_any_change')
    allow_host_change = args.pop('allow_host_change', False) or allow_any_change
    allow_version_change = args.pop('allow_version_change', False) or allow_any_change

    config = TrialBuilder().fetch_full_config(args)
    TrialBuilder().build_database(dict(database=config['database']))

    host = config['host']
    version = config['version']

    config.pop('database', None)
    config.pop('resources', None)
    config.pop('debug', None)
    config.pop('id', None)
    tags = [tag for tag in config.pop('tags', "").split(";") if tag]

    query = {
        'tags': {'$all': tags},
        'registry.status': {'$in': status.RESERVABLE}
        }

    if not tags:
        query.pop('tags')

    trials_seen = set()
    new_trials = True

    while new_trials:
        new_trials = False

        for trial in fetch_new_trials(query, trials_seen):
            new_trials = True
            execute_trial(consumer, trial, host, version, allow_host_change, allow_version_change)


def fetch_new_trials(query, trials_seen):
    for trial in Database().read(Trial.trial_report_collection, query, {'registry.status': 1}):
        if trial['_id'] not in trials_seen:
            trial = TrialNode.view(trial['_id'])
            if trial is None:
                continue

            trials_seen.add(trial.id)
            yield trial


def execute_trial(consumer, trial, host, version, allow_host_change, allow_version_change):
    trial.update()
    try:
        trial.status
    except AttributeError:
        print("Attribute error, now marked as broken: {}".format(trial.short_id))
        trial = TrialNode.load(trial.id)
        trial.reserve()
        trial.running()
        trial.broken()
        trial.save()
        return

    if trial.status not in status.RESERVABLE:
        print("Skipping {}; status changed to {} in a concurrent "
              "process".format(trial.short_id, trial.status))
        return

    if trial.host and trial.host != host and not allow_host_change:
        print("Skipping {}; different host".format(trial.short_id))
        return

    if trial.version and trial.version != version and not allow_version_change:
        print("Skipping {}; different code version".format(trial.short_id))
        return

    # Branch if there was any allowed change
    if trial.version != version or trial.host != host:
        if trial.version != version:
            print("Branching {} because of different code version".format(trial.short_id))

        if trial.host != host:
            print("Branching {} because of different host".format(trial.short_id))

        try:
            trial = TrialNode.branch(trial.id, **config)
        except DuplicateKeyError:
            print("Skipping {}; branch already exist".format(trial.short_id))
            return
    else:
        trial = TrialNode.load(trial.id)

    try:
        consumer.consume(trial)
    except BaseException as e:
        print("Error: Trial {} is broken".format(trial.short_id))
        print()
        print("You can check log with the following command:")
        print("$ kleio cat --stderr {}".format(trial.short_id))
        print()


def unique_worker(consumer, args):
    tags = [tag for tag in args.pop('tags', "").split(";") if tag]
    switchover = args.pop('switch_over', False)
    allow_any_change = args.pop('allow_any_change')
    allow_code_change = args.pop('allow_code_change', False) or allow_any_change
    allow_host_change = args.pop('allow_host_change', False) or allow_any_change
    allow_version_change = args.pop('allow_version_change', False) or allow_any_change

    trial = TrialBuilder().build_from(args)
    if trial.status == 'broken' and switchover:
        trial.switchover()

    for tag in tags:
        if tag not in trial._tags.get():
            trial._tags.append(tag)
        # trial.save()
    consumer.consume(trial)


# If selected trial has no host, --allow-change-host
# If selected trial has no version, --allow-change-host --allow-change-code


def default(args):
    root_working_dir = args.pop('root_working_dir', '.')
    capture = args.pop('capture', False)
    debug = args.get('debug', False)

    consumer = Consumer(root_working_dir, capture, debug)

    if not args['commandline']:
        sequential_worker(consumer, args)
    else:
        unique_worker(consumer, args)
