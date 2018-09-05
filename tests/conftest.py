#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Common fixtures and utils for unittests and functional tests."""
import os

import numpy
from pymongo import MongoClient
import pytest
import yaml

from kleio.core.io import resolve_config
from kleio.core.io.database import Database
from kleio.core.io.database.mongodb import MongoDB


@pytest.fixture(scope='session')
def database():
    """Return Mongo database object to test with example entries."""
    client = MongoClient(username='user', password='pass', authSource='kleio_test')
    database = client.kleio_test
    yield database
    client.close()


@pytest.fixture()
def null_db_instances():
    """Nullify singleton instance so that we can assure independent instantiation tests."""
    Database.instance = None
    MongoDB.instance = None


@pytest.fixture(scope='function')
def seed():
    """Return a fixed ``numpy.random.RandomState`` and global seed."""
    seed = 5
    rng = numpy.random.RandomState(seed)
    numpy.random.seed(seed)
    return rng


@pytest.fixture
def version_XYZ(monkeypatch):
    """Force kleio version XYZ on output of resolve_config.fetch_metadata"""
    non_patched_fetch_metadata = resolve_config.fetch_metadata

    def fetch_metadata(cmdargs):
        metadata = non_patched_fetch_metadata(cmdargs)
        metadata['kleio_version'] = 'XYZ'
        return metadata
    monkeypatch.setattr(resolve_config, "fetch_metadata", fetch_metadata)


@pytest.fixture()
def create_db_instance(null_db_instances, clean_db):
    """Create and save a singleton database instance."""
    try:
        db = Database(of_type='MongoDB', name='kleio_test',
                      username='user', password='pass')
    except ValueError:
        db = Database()

    return db
