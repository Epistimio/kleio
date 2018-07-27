#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Collection of tests for :mod:`kleio.core.io.database.mongodb`."""

from datetime import datetime
import functools

import pymongo
from pymongo import MongoClient
import pytest

from kleio.core.io.database import Database, DatabaseError, DuplicateKeyError
from kleio.core.io.database.mongodb import AUTH_FAILED_MESSAGES, MongoDB


@pytest.fixture(scope='module')
def kleio_db():
    """Return MongoDB wrapper instance initiated with test opts."""
    MongoDB.instance = None
    kleio_db = MongoDB(username='user', password='pass', name='kleio_test')
    return kleio_db


@pytest.fixture()
def patch_mongo_client(monkeypatch):
    """Patch ``pymongo.MongoClient`` to force serverSelectionTimeoutMS to 1."""
    def mock_class(*args, **kwargs):
        # 1 sec, defaults to 20 secs otherwise
        kwargs['serverSelectionTimeoutMS'] = 1.
        # NOTE: Can't use pymongo.MongoClient otherwise there is an infinit
        # recursion; mock(mock(mock(mock(...(MongoClient)...))))
        return MongoClient(*args, **kwargs)

    monkeypatch.setattr('pymongo.MongoClient', mock_class)


@pytest.mark.usefixtures("null_db_instances")
class TestConnection(object):
    """Create a :class:`kleio.core.io.database.mongodb.MongoDB`, check connection cases."""

    @pytest.mark.usefixtures("patch_mongo_client")
    def test_bad_connection(self, monkeypatch):
        """Raise when connection cannot be achieved."""
        monkeypatch.setattr(
            MongoDB, "initiate_connection",
            MongoDB.initiate_connection.__wrapped__)
        with pytest.raises(pymongo.errors.ConnectionFailure) as exc_info:
            MongoDB(host='asdfada', port=123, name='kleio',
                    username='uasdfaf', password='paasdfss')

        monkeypatch.undo()

        # Verify that the wrapper converts it properly to DatabaseError
        with pytest.raises(DatabaseError) as exc_info:
            MongoDB(host='asdfada', port=123, name='kleio',
                    username='uasdfaf', password='paasdfss')
        assert "Connection" in str(exc_info.value)

    def test_bad_authentication(self, monkeypatch):
        """Raise when authentication cannot be achieved."""
        monkeypatch.setattr(
            MongoDB, "initiate_connection",
            MongoDB.initiate_connection.__wrapped__)
        with pytest.raises(pymongo.errors.OperationFailure) as exc_info:
            MongoDB(name='kleio_test', username='uasdfaf', password='paasdfss')
        assert any(m in str(exc_info.value) for m in AUTH_FAILED_MESSAGES)

        monkeypatch.undo()

        with pytest.raises(DatabaseError) as exc_info:
            MongoDB(name='kleio_test', username='uasdfaf', password='paasdfss')
        assert "Authentication" in str(exc_info.value)

    def test_connection_with_uri(self):
        """Check the case when connecting with ready `uri`."""
        kleio_db = MongoDB('mongodb://user:pass@localhost/kleio_test')
        assert kleio_db.host == 'localhost'
        assert kleio_db.port == 27017
        assert kleio_db.username == 'user'
        assert kleio_db.password == 'pass'
        assert kleio_db.name == 'kleio_test'

    def test_overwrite_uri(self):
        """Check the case when connecting with ready `uri`."""
        kleio_db = MongoDB('mongodb://user:pass@localhost:27017/kleio_test',
                           port=1231, name='kleio', username='lala',
                           password='pass')
        assert kleio_db.host == 'localhost'
        assert kleio_db.port == 27017
        assert kleio_db.username == 'user'
        assert kleio_db.password == 'pass'
        assert kleio_db.name == 'kleio_test'

    def test_singleton(self):
        """Test that MongoDB class is a singleton."""
        kleio_db = MongoDB(username='user', password='pass', name='kleio_test')
        # reinit connection does not change anything
        kleio_db.initiate_connection()
        kleio_db.close_connection()
        assert MongoDB() is kleio_db


@pytest.mark.usefixtures("clean_db")
class TestExceptionWrapper(object):
    """Call to methods wrapped with `mongodb_exception_wrapper()`."""

    def test_duplicate_key_error(self, monkeypatch, kleio_db, exp_config):
        """Should raise generic DuplicateKeyError."""
        # Add unique indexes to force trigger of DuplicateKeyError on write()
        kleio_db.ensure_index('experiments',
                              [('name', Database.ASCENDING),
                               ('metadata.user', Database.ASCENDING)],
                              unique=True)

        config_to_add = exp_config[0][0]
        config_to_add.pop('_id')

        query = {'_id': exp_config[0][1]['_id']}

        # Make sure it raises pymongo.errors.DuplicateKeyError when there is no
        # wrapper
        monkeypatch.setattr(
            kleio_db, "read_and_write",
            functools.partial(kleio_db.read_and_write.__wrapped__, kleio_db))
        with pytest.raises(pymongo.errors.DuplicateKeyError) as exc_info:
            kleio_db.read_and_write('experiments', query, config_to_add)

        monkeypatch.undo()

        # Verify that the wrapper converts it properly to DuplicateKeyError
        with pytest.raises(DuplicateKeyError) as exc_info:
            kleio_db.read_and_write('experiments', query, config_to_add)
        assert "duplicate key error" in str(exc_info.value)

    def test_bulk_duplicate_key_error(self, monkeypatch, kleio_db, exp_config):
        """Should raise generic DuplicateKeyError."""
        # Make sure it raises pymongo.errors.BulkWriteError when there is no
        # wrapper
        monkeypatch.setattr(
            kleio_db, "write",
            functools.partial(kleio_db.write.__wrapped__, kleio_db))
        with pytest.raises(pymongo.errors.BulkWriteError) as exc_info:
            kleio_db.write('experiments', exp_config[0])

        monkeypatch.undo()

        # Verify that the wrapper converts it properly to DuplicateKeyError
        with pytest.raises(DuplicateKeyError) as exc_info:
            kleio_db.write('experiments', exp_config[0])
        assert "duplicate key error" in str(exc_info.value)

    def test_non_converted_errors(self, kleio_db, exp_config):
        """Should raise OperationFailure.

        This is because _id inside exp_config[0][0] cannot be set. It is an
        immutable key of the collection.

        """
        config_to_add = exp_config[0][0]

        query = {'_id': exp_config[0][1]['_id']}

        with pytest.raises(pymongo.errors.OperationFailure):
            kleio_db.read_and_write('experiments', query, config_to_add)


@pytest.mark.usefixtures("clean_db")
class TestEnsureIndex(object):
    """Calls to :meth:`kleio.core.io.database.mongodb.MongoDB.ensure_index`."""

    def test_new_index(self, kleio_db):
        """Index should be added to mongo database"""
        assert "status_1" not in kleio_db._db.trials.index_information()
        kleio_db.ensure_index('trials', 'status')
        assert "status_1" in kleio_db._db.trials.index_information()

    def test_existing_index(self, kleio_db):
        """Index should be added to mongo database and reattempt should do nothing"""
        assert "status_1" not in kleio_db._db.trials.index_information()
        kleio_db.ensure_index('trials', 'status')
        assert "status_1" in kleio_db._db.trials.index_information()
        kleio_db.ensure_index('trials', 'status')
        assert "status_1" in kleio_db._db.trials.index_information()

    def test_ordered_index(self, kleio_db):
        """Sort order should be added to index"""
        assert "end_time_-1" not in kleio_db._db.trials.index_information()
        kleio_db.ensure_index('trials', [('end_time', MongoDB.DESCENDING)])
        assert "end_time_-1" in kleio_db._db.trials.index_information()

    def test_compound_index(self, kleio_db):
        """Tuple of Index should be added as a compound index."""
        assert "name_1_metadata.user_1" not in kleio_db._db.experiments.index_information()
        kleio_db.ensure_index('experiments',
                              [('name', MongoDB.ASCENDING),
                               ('metadata.user', MongoDB.ASCENDING)])
        assert "name_1_metadata.user_1" in kleio_db._db.experiments.index_information()

    def test_unique_index(self, kleio_db):
        """Index should be set as unique in mongo database's index information."""
        assert "name_1_metadata.user_1" not in kleio_db._db.experiments.index_information()
        kleio_db.ensure_index('experiments',
                              [('name', MongoDB.ASCENDING),
                               ('metadata.user', MongoDB.ASCENDING)],
                              unique=True)
        index_information = kleio_db._db.experiments.index_information()
        assert "name_1_metadata.user_1" in index_information
        assert index_information["name_1_metadata.user_1"]['unique']


@pytest.mark.usefixtures("clean_db")
class TestRead(object):
    """Calls to :meth:`kleio.core.io.database.mongodb.MongoDB.read`."""

    def test_read_experiment(self, exp_config, kleio_db):
        """Fetch a whole experiment entries."""
        loaded_config = kleio_db.read(
            'trials', {'experiment': 'supernaedo2', 'status': 'new'})
        assert loaded_config == [exp_config[1][3], exp_config[1][4]]

        loaded_config = kleio_db.read(
            'trials',
            {'experiment': 'supernaedo2',
             'submit_time': exp_config[1][3]['submit_time']})
        assert loaded_config == [exp_config[1][3]]
        assert loaded_config[0]['_id'] == exp_config[1][3]['_id']

    def test_read_with_id(self, exp_config, kleio_db):
        """Query using ``_id`` key."""
        loaded_config = kleio_db.read('experiments', {'_id': exp_config[0][2]['_id']})
        assert loaded_config == [exp_config[0][2]]

    def test_read_default(self, exp_config, kleio_db):
        """Fetch value(s) from an entry."""
        value = kleio_db.read(
            'experiments', {'name': 'supernaedo2', 'metadata.user': 'tsirif'},
            selection={'algorithms': 1, '_id': 0})
        assert value == [{'algorithms': exp_config[0][0]['algorithms']}]

    def test_read_nothing(self, kleio_db):
        """Fetch value(s) from an entry."""
        value = kleio_db.read(
            'experiments', {'name': 'not_found', 'metadata.user': 'tsirif'},
            selection={'algorithms': 1})
        assert value == []

    def test_read_trials(self, exp_config, kleio_db):
        """Fetch value(s) from an entry."""
        value = kleio_db.read(
            'trials',
            {'experiment': 'supernaedo2',
             'submit_time': {'$gte': datetime(2017, 11, 23, 0, 0, 0)}})
        assert value == exp_config[1][2:7]

        value = kleio_db.read(
            'trials',
            {'experiment': 'supernaedo2',
             'submit_time': {'$gt': datetime(2017, 11, 23, 0, 0, 0)}})
        assert value == exp_config[1][3:7]


@pytest.mark.usefixtures("clean_db")
class TestWrite(object):
    """Calls to :meth:`kleio.core.io.database.mongodb.MongoDB.write`."""

    def test_insert_one(self, database, kleio_db):
        """Should insert a single new entry in the collection."""
        item = {'exp_name': 'supernaekei',
                'user': 'tsirif'}
        count_before = database.experiments.count()
        # call interface
        assert kleio_db.write('experiments', item) is True
        assert database.experiments.count() == count_before + 1
        value = database.experiments.find_one({'exp_name': 'supernaekei'})
        assert value == item

    def test_insert_many(self, database, kleio_db):
        """Should insert two new entry (as a list) in the collection."""
        item = [{'exp_name': 'supernaekei2',
                 'user': 'tsirif'},
                {'exp_name': 'supernaekei3',
                 'user': 'tsirif'}]
        count_before = database.experiments.count()
        # call interface
        assert kleio_db.write('experiments', item) is True
        assert database.experiments.count() == count_before + 2
        value = database.experiments.find_one({'exp_name': 'supernaekei2'})
        assert value == item[0]
        value = database.experiments.find_one({'exp_name': 'supernaekei3'})
        assert value == item[1]

    def test_update_many_default(self, database, kleio_db):
        """Should match existing entries, and update some of their keys."""
        filt = {'metadata.user': 'tsirif'}
        count_before = database.experiments.count()
        # call interface
        assert kleio_db.write('experiments', {'pool_size': 16}, filt) is True
        assert database.experiments.count() == count_before
        value = list(database.experiments.find({}))
        assert value[0]['pool_size'] == 16
        assert value[1]['pool_size'] == 16
        assert value[2]['pool_size'] == 16
        assert value[3]['pool_size'] == 2

    def test_update_with_id(self, exp_config, database, kleio_db):
        """Query using ``_id`` key."""
        filt = {'_id': exp_config[0][1]['_id']}
        count_before = database.experiments.count()
        # call interface
        assert kleio_db.write('experiments', {'pool_size': 36}, filt) is True
        assert database.experiments.count() == count_before
        value = list(database.experiments.find())
        assert value[0]['pool_size'] == 2
        assert value[1]['pool_size'] == 36
        assert value[2]['pool_size'] == 2

    def test_upsert_with_id(self, database, kleio_db):
        """Query with a non-existent ``_id`` should upsert something."""
        filt = {'_id': 'lalalathisisnew'}
        count_before = database.experiments.count()
        # call interface
        assert kleio_db.write('experiments', {'pool_size': 66}, filt) is True
        assert database.experiments.count() == count_before + 1
        value = list(database.experiments.find(filt))
        assert len(value) == 1
        assert len(value[0]) == 2
        assert value[0]['_id'] == 'lalalathisisnew'
        assert value[0]['pool_size'] == 66


@pytest.mark.usefixtures("clean_db")
class TestReadAndWrite(object):
    """Calls to :meth:`kleio.core.io.database.mongodb.MongoDB.read_and_write`."""

    def test_read_and_write_one(self, database, kleio_db, exp_config):
        """Should read and update a single entry in the collection."""
        # Make sure there is only one match
        documents = kleio_db.read(
            'experiments',
            {'name': 'supernaedo2', 'metadata.user': 'dendi'})
        assert len(documents) == 1

        # Find and update atomically
        loaded_config = kleio_db.read_and_write(
            'experiments',
            {'name': 'supernaedo2', 'metadata.user': 'dendi'},
            {'pool_size': 'lalala'})
        exp_config[0][3]['pool_size'] = 'lalala'
        assert loaded_config == exp_config[0][3]

    def test_read_and_write_many(self, database, kleio_db, exp_config):
        """Should update only one entry."""
        # Make sure there is many matches
        documents = kleio_db.read('experiments', {'name': 'supernaedo2'})
        assert len(documents) > 1

        # Find many and update first one only
        loaded_config = kleio_db.read_and_write(
            'experiments',
            {'name': 'supernaedo2'},
            {'pool_size': 'lalala'})

        exp_config[0][0]['pool_size'] = 'lalala'
        assert loaded_config == exp_config[0][0]

        # Make sure it only changed the first document found
        documents = kleio_db.read('experiments', {'name': 'supernaedo2'})
        assert documents[0]['pool_size'] == 'lalala'
        assert documents[1]['pool_size'] != 'lalala'

    def test_read_and_write_no_match(self, database, kleio_db):
        """Should return None when there is no match."""
        loaded_config = kleio_db.read_and_write(
            'experiments',
            {'name': 'lalala'},
            {'pool_size': 'lalala'})

        assert loaded_config is None


@pytest.mark.usefixtures("clean_db")
class TestRemove(object):
    """Calls to :meth:`kleio.core.io.database.mongodb.MongoDB.remove`."""

    def test_remove_many_default(self, exp_config, database, kleio_db):
        """Should match existing entries, and delete them all."""
        filt = {'metadata.user': 'tsirif'}
        count_before = database.experiments.count()
        count_filt = database.experiments.count(filt)
        # call interface
        assert kleio_db.remove('experiments', filt) is True
        assert database.experiments.count() == count_before - count_filt
        assert database.experiments.count() == 1
        assert list(database.experiments.find()) == [exp_config[0][3]]

    def test_remove_with_id(self, exp_config, database, kleio_db):
        """Query using ``_id`` key."""
        filt = {'_id': exp_config[0][0]['_id']}
        count_before = database.experiments.count()
        # call interface
        assert kleio_db.remove('experiments', filt) is True
        assert database.experiments.count() == count_before - 1
        assert list(database.experiments.find()) == exp_config[0][1:]


@pytest.mark.usefixtures("clean_db")
class TestCount(object):
    """Calls :meth:`kleio.core.io.database.mongodb.MongoDB.count`."""

    def test_count_default(self, exp_config, kleio_db):
        """Call just with collection name."""
        found = kleio_db.count('trials')
        assert found == len(exp_config[1])

    def test_count_query(self, exp_config, kleio_db):
        """Call with a query."""
        found = kleio_db.count('trials', {'status': 'completed'})
        assert found == len([x for x in exp_config[1] if x['status'] == 'completed'])

    def test_count_query_with_id(self, exp_config, kleio_db):
        """Call querying with unique _id."""
        found = kleio_db.count('trials', {'_id': exp_config[1][2]['_id']})
        assert found == 1

    def test_count_nothing(self, kleio_db):
        """Call with argument that will not find anything."""
        found = kleio_db.count('experiments', {'name': 'lalalanotfound'})
        assert found == 0
