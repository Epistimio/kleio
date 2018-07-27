#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
:mod:`kleio.core.cli` -- Functions that define console scripts
================================================================

.. module:: cli
   :platform: Unix
   :synopsis: Helper functions to setup an experiment and execute it.

"""
import logging

from kleio.core.cli.base import KleioArgsParser
from kleio.core.utils import module_import

log = logging.getLogger(__name__)


def load_modules_parser(kleio_parser):
    """Search through the `cli` folder for any module containing a `get_parser` function"""
    modules = module_import.load_modules_in_path('kleio.core.cli',
                                                 lambda m: hasattr(m, 'add_subparser'))

    for module in modules:
        get_parser = getattr(module, 'add_subparser')
        get_parser(kleio_parser.get_subparsers())


def main(argv=None):
    """Entry point for `kleio.core` functionality."""
    # Fetch experiment name, user's script path and command line arguments
    # Use `-h` option to show help

    kleio_parser = KleioArgsParser()

    load_modules_parser(kleio_parser)

    kleio_parser.execute(argv)

    return 0


if __name__ == "__main__":
    main()
