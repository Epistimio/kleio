# -*- coding: utf-8 -*-
"""
:mod:`kleio.core.cli` -- Base class and function utilities for cli
==================================================================

.. module:: cli
   :platform: Unix
   :synopsis: Kleiṓ main parser class and helper functions to parse command-line options

"""
import argparse
import logging
import textwrap
import sys

import kleio
from kleio.core.cli.default import add_default_subparser


CLI_DOC_HEADER = """
kleio:
  Kleiṓ cli script for asynchronous distributed optimization

"""


def set_default_subparser(self, name, args=None, positional_args=0):
    """default subparser selection. Call after setup, just before parse_args()
    name: is the name of the subparser to call by default
    args: if set is the argument list handed to parse_args()

    , tested with 2.7, 3.2, 3.3, 3.4
    it works with 2.6 assuming argparse is installed
    """
    subparser_found = False
    existing_default = False # check if default parser previously defined
    for arg in sys.argv[1:]:
        if arg in ['-h', '--help']:  # global help if no subparser
            break
    else:
        for x in self._subparsers._actions:
            if not isinstance(x, argparse._SubParsersAction):
                continue
            for sp_name in list(x._name_parser_map.keys()):
                if sp_name in sys.argv[1:]:
                    subparser_found = True
                if sp_name == name: # check existance of default parser
                    existing_default = True
        if not subparser_found:
            # If the default subparser is not among the existing ones,
            # create a new parser.
            # As this is called just before 'parse_args', the default
            # parser created here will not pollute the help output.

            if not existing_default:
                for x in self._subparsers._actions:
                    if not isinstance(x, argparse._SubParsersAction):
                        continue
                    add_default_subparser(x, name)
                    break # this works OK, but should I check further?

            # insert default in last position before global positional
            # arguments, this implies no global options are specified after
            # first positional argument
            if args is None:
                args = sys.argv

            # TODO: Only check first positional argument 
            if name in sys.argv[1:]:
                return

            positional_args = 0
            for i in range(1, len(args[1:])):
                if not args[i].startswith("-"):
                    positional_args = i
                    break

            args.insert(positional_args, name)


argparse.ArgumentParser.set_default_subparser = set_default_subparser


class KleioArgsParser:
    """Parser object handling the upper-level parsing of Kleio's arguments."""

    def __init__(self, description=CLI_DOC_HEADER):
        """Create the pre-command arguments"""
        self.description = description

        self.parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent(description))

        self.parser.add_argument(
            '-V', '--version',
            action='version', version='kleio ' + kleio.core.__version__)

        self.parser.add_argument(
            '-v', '--verbose',
            action='count', default=0,
            help="logging levels of information about the process (-v: INFO. -vv: DEBUG)")

        self.parser.add_argument(
            '-d', '--debug', action='store_true',
            help="Use debugging mode with EphemeralDB.")

        self.subparsers = self.parser.add_subparsers(help='sub-command help')

    def get_subparsers(self):
        """Return the subparser object for this parser."""
        return self.subparsers

    def parse(self, argv):
        """Call argparse and generate a dictionary of arguments' value"""
        self.parser.set_default_subparser('run', args=argv, positional_args=1)
        args = vars(self.parser.parse_args(argv))

        verbose = args.pop('verbose', 0)
        levels = {0: logging.WARNING,
                  1: logging.INFO,
                  2: logging.DEBUG}
        logging.basicConfig(level=levels.get(verbose, logging.DEBUG))

        function = args.pop('func')
        return args, function

    def execute(self, argv):
        """Execute main function of the subparser"""
        args, function = self.parse(argv)
        function(args)


def get_basic_args_group(parser):
    """Return the basic arguments for any command."""
    basic_args_group = parser.add_argument_group(
        "Kleio arguments (optional)",
        description="These arguments determine kleio's behaviour")

    basic_args_group.add_argument('-c', '--config', type=argparse.FileType('r'),
                                  metavar='path-to-config', help="user provided "
                                  "kleio configuration file")

    return basic_args_group


def get_version_args_group(parser):

    version_group = parser.add_argument_group(
        "Execution version related arguments",
        description="These argument determine automated branching or version conflicts.")

    version_group.add_argument(
        '--allow-code-change', action='store_true',
        help="")

    version_group.add_argument(
        '--allow-version-change', action='store_true',
        help="")

    version_group.add_argument(
        '--allow-host-change', action='store_true',
        help="")

    version_group.add_argument(
        '--allow-any-change', action='store_true',
        help="")

    return version_group


def get_user_args_group(parser):
    """
    Return the user group arguments for any command.
    User group arguments are composed of the user script and the user args
    """
    usergroup = parser.add_argument_group(
        "User script related arguments",
        description="These arguments determine user's script behaviour "
                    "and they can serve as kleio's parameter declaration.")

    usergroup.add_argument(
        'commandline', nargs=argparse.REMAINDER, metavar='...',
        help="Command line of user script. A configuration "
             "file intended to be used with 'userscript' must be given as a path "
             "in the **first positional** argument OR using `--config=<path>` "
             "keyword argument.")

    return usergroup
