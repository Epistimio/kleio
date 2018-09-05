#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Example usage and tests for :mod:`kleio.core.io.cmdline_parser`."""
from collections import OrderedDict
import os

import pytest

from kleio.core.io.cmdline_parser import CmdlineParser


def test_arg_to_key():
    cmdline_parser = CmdlineParser()
    assert cmdline_parser.arg_to_key("-c") == "c"
    assert cmdline_parser.arg_to_key("--test") == "test"
    assert cmdline_parser.arg_to_key("--test.test") == "test.test"
    assert cmdline_parser.arg_to_key("--test_test") == "test__test"
    assert cmdline_parser.arg_to_key("--test__test") == "test____test"
    assert cmdline_parser.arg_to_key("--test-test") == "test_test"
    assert cmdline_parser.arg_to_key("--test-some=thing") == "test_some"
    assert cmdline_parser.arg_to_key("--test.some=thing") == "test.some"
    assert cmdline_parser.arg_to_key("--test-some=thing=is=weird") == "test_some"


def test_bad_arg_to_key():
    cmdline_parser = CmdlineParser()
    with pytest.raises(ValueError):
        assert cmdline_parser.arg_to_key("-c-c")

    with pytest.raises(ValueError):
        assert cmdline_parser.arg_to_key("--c")

    with pytest.raises(ValueError):
        assert cmdline_parser.arg_to_key("--c")


def test_key_to_arg():
    cmdline_parser = CmdlineParser()
    assert cmdline_parser.key_to_arg("c") == "-c"
    assert cmdline_parser.key_to_arg("test") == "--test"
    assert cmdline_parser.key_to_arg("test.test") == "--test.test"
    assert cmdline_parser.key_to_arg("test__test") == "--test_test"
    assert cmdline_parser.key_to_arg("test____test") == "--test__test"
    assert cmdline_parser.key_to_arg("test_test") == "--test-test"
    assert cmdline_parser.key_to_arg("test_some") == "--test-some"
    assert cmdline_parser.key_to_arg("test.some") == "--test.some"
    assert cmdline_parser.key_to_arg("test__some") == "--test_some"


def test_parse_paths(monkeypatch):
    monkeypatch.chdir(os.path.dirname(__file__))
    cmdline_parser = CmdlineParser()
    assert cmdline_parser.parse_paths(__file__) == os.path.abspath(__file__)

    values = ['test_resolve_config.py', 'test', 'nada', __file__]
    parsed_values = cmdline_parser.parse_paths(values)
    assert parsed_values[0] == os.path.abspath('test_resolve_config.py')
    assert parsed_values[1] == 'test'
    assert parsed_values[2] == 'nada'
    assert parsed_values[3] == os.path.abspath(__file__)


def test_parse_arguments():
    cmdline_parser = CmdlineParser()

    assert (
        cmdline_parser.parse_arguments(
            "python script.py some pos args "
            "--with args --and multiple args --plus --booleans".split(" ")) == 
        [['_pos_0', 'python'], ['_pos_1', 'script.py'], ['_pos_2', 'some'], ['_pos_3', 'pos'],
         ['_pos_4', 'args'], ['with', 'args'], ['and', ['multiple', 'args']], ['plus', True],
         ['booleans', True]])



def test_parse_arguments_configuration():
    cmdline_parser = CmdlineParser()

    configuration = cmdline_parser.parse(
            "python script.py some pos args "
            "--with args --and multiple args --plus --booleans".split(" "))
    assert configuration == OrderedDict(
        [['_pos_0', 'python'], ['_pos_1', 'script.py'], ['_pos_2', 'some'], ['_pos_3', 'pos'],
         ['_pos_4', 'args'], ['with', 'args'], ['and', ['multiple', 'args']], ['plus', True],
         ['booleans', True]])


def test_parse_arguments_template():
    cmdline_parser = CmdlineParser()

    configuration = cmdline_parser.parse(
            "python script.py some pos args "
            "--with args --and multiple args --plus --booleans".split(" "))

    assert (
        cmdline_parser.template ==
        ['{_pos_0}', '{_pos_1}', '{_pos_2}', '{_pos_3}', '{_pos_4}', '--with', '{with}', '--and',
         '{and[0]}', '{and[1]}', '--plus', '--booleans'])



def test_parse_arguments_bad_command():
    cmdline_parser = CmdlineParser()

    with pytest.raises(ValueError) as exc_info:
        configuration = cmdline_parser.parse(
                "python script.py some pos args "
                "--with args --and multiple args --plus --booleans "
                "--and dummy.yaml".split(" "))

    assert "Two arguments have the same name: and" in str(exc_info.value)


def test_parse_arguments_configuration_file(monkeypatch):
    monkeypatch.chdir(os.path.dirname(__file__))
    assert os.path.exists('dummy.yaml')
    cmdline_parser = CmdlineParser()

    configuration = cmdline_parser.parse(
            "python script.py some pos args "
            "--with args --and multiple args --plus --booleans "
            "--also dummy.yaml".split(" "))

    assert (
        cmdline_parser.template ==
        ['{_pos_0}', '{_pos_1}', '{_pos_2}', '{_pos_3}', '{_pos_4}', '--with', '{with}', '--and',
         '{and[0]}', '{and[1]}', '--plus', '--booleans', '--also', '{also}'])

    assert configuration['also'] == {
        'file': os.path.abspath('dummy.yaml'),
        'content': {
            'another': 1.0,
            'one': 'value', 
            'plus': {
                'done': 2, 
                'some': {
                    'hierarchical': 'values'}
                }
            }
        }



def test_parse_arguments_multiple_configuration_files(monkeypatch):
    monkeypatch.chdir(os.path.dirname(__file__))
    assert os.path.exists('dummy.yaml')
    assert os.path.exists('dummy2.yaml')
    cmdline_parser = CmdlineParser()

    command = ("python script.py some pos args "
               "--config dummy2.yaml "
               "--with args --and multiple args --plus --booleans "
               "--also dummy.yaml")

    configuration = cmdline_parser.parse(command.split(" "))

    assert (
        cmdline_parser.template ==
        ['{_pos_0}', '{_pos_1}', '{_pos_2}', '{_pos_3}', '{_pos_4}', '--config', '{config}', '--with', '{with}', '--and',
         '{and[0]}', '{and[1]}', '--plus', '--booleans', '--also', '{also}'])

    assert configuration['also'] == {
        'file': os.path.abspath('dummy.yaml'),
        'content': {
            'another': 1.0,
            'one': 'value', 
            'plus': {
                'done': 2, 
                'some': {
                    'hierarchical': 'values'}
                }
            }
        }

    assert configuration['config'] == {
        'file': os.path.abspath('dummy2.yaml'),
        'content': {
            'two': 'value',
            'heh': 3, 
            'voici': 'voila'
            }
        }

    assert (
        cmdline_parser.format(configuration) == 
        command.replace('dummy.yaml', os.path.abspath('dummy.yaml')).replace('dummy2.yaml', os.path.abspath('dummy2.yaml')))


def test_parse_branching_arguments_template():
    cmdline_parser = CmdlineParser()

    command = ("python script.py some pos args "
               "--with args --and multiple args --plus --booleans ")

    configuration = cmdline_parser.parse(command.split(" "))
    assert (
        cmdline_parser.template ==
        ['{_pos_0}', '{_pos_1}', '{_pos_2}', '{_pos_3}', '{_pos_4}', '--with', '{with}', '--and',
         '{and[0]}', '{and[1]}', '--plus', '--booleans'])

    branch_configuration = cmdline_parser.parse("--with something --to update".split(" "))

    assert branch_configuration == {
        'with': 'something',
        'to': 'update'}

    assert (
        cmdline_parser.template ==
        ['{_pos_0}', '{_pos_1}', '{_pos_2}', '{_pos_3}', '{_pos_4}', '--with', '{with}', '--and',
         '{and[0]}', '{and[1]}', '--plus', '--booleans', '--to', '{to}'])


def test_parse_branching_arguments_format(monkeypatch):
    monkeypatch.chdir(os.path.dirname(__file__))

    cmdline_parser = CmdlineParser()

    command = ("python script.py some pos args "
               "--with args --and multiple args --plus --booleans ")

    configuration = cmdline_parser.parse(command.split(" "))
    print(cmdline_parser.template)
    assert cmdline_parser.format(configuration) == command.strip(" ")

    branch_configuration = cmdline_parser.parse("--with something --to update".split(" "))
    print(configuration)
    print(cmdline_parser.template)
    print(branch_configuration)
    configuration.update(branch_configuration)

    assert (
        cmdline_parser.format(configuration) ==
        command.replace("--with args", "--with something").strip(" ") + " --to update")
