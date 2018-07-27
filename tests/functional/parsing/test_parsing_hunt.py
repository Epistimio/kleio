#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Perform functional tests for the parsing of the `hunt` command."""
import argparse
import os

import pytest

from kleio.core.cli import hunt


def _create_parser(need_subparser=True):
    parser = argparse.ArgumentParser()

    if need_subparser:
        subparsers = parser.add_subparsers()
        return parser, subparsers

    return parser


@pytest.mark.usefixtures("clean_db")
def test_hunt_command_full_parsing(database, monkeypatch):
    """Test the parsing of the `hunt` command"""
    monkeypatch.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser, subparsers = _create_parser()
    args_list = ["hunt", "-n", "test",
                 "--config", "./kleio_config_random.yaml",
                 "--max-trials", "400", "--pool-size", "4",
                 "./black_box.py", "-x~normal(1,1)"]

    hunt.add_subparser(subparsers)
    subparsers.choices['hunt'].set_defaults(func='')

    args = vars(parser.parse_args(args_list))
    assert args['name'] == 'test'
    assert args['config'].name == './kleio_config_random.yaml'
    assert args['user_args'] == ['./black_box.py', '-x~normal(1,1)']
    assert args['pool_size'] == 4
    assert args['max_trials'] == 400
