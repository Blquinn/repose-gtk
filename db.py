import json
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from typing import List, Iterable
from collections import namedtuple
import sqlite3
import threading

from config import DATA_DIR
from models import RequestModel, CollectionModel, RequestTreeNode, FolderModel


db_local = threading.local()

log = logging.getLogger(__name__)


def initialize_db_thread(*args, **kwargs):
    """Initialize each thread pool worker with its own db connection"""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    db_local.db = get_connection()
    log.info('Initialized db in thread %s', threading.get_ident())


# Serialize all access to sqlite connection via this single threaded executor.
# All access to sqlite should happen through the executor.
DB_EXECUTOR = ThreadPoolExecutor(max_workers=1, initializer=initialize_db_thread)


def get_connection(path: str = None) -> sqlite3.Connection:
    path = path or f'{DATA_DIR}/storage.db'
    db = sqlite3.connect(path, 30.0)
    try:
        db.execute("""
        create table collections (
            id text primary key,
            name text unique not null
        );
        """)

        db.execute("""
        create table requests (
            id text primary key,
            collection_id text references collections,
            parent_id text references requests,
            folder_json text, 
            request_json text 
        );
        """)
    except sqlite3.OperationalError:
        pass

    return db


NodeRecord = namedtuple('NodeRecord', ['pk', 'collection_pk', 'parent_pk', 'folder_json', 'request_json'])


def map_record_to_node(rec: NodeRecord) -> RequestTreeNode:
    if rec.folder_json:
        folder = FolderModel(**json.loads(rec.folder_json))
        return RequestTreeNode(pk=rec.pk, parent_pk=rec.parent_pk, folder=folder, collection_pk=rec.collection_pk)

    req = RequestModel(**json.loads(rec.request_json))
    return RequestTreeNode(pk=rec.pk, parent_pk=rec.parent_pk, request=req, collection_pk=rec.collection_pk)


def map_records(recs: Iterable[NodeRecord]) -> List[RequestTreeNode]:
    nodes = (map_record_to_node(rec) for rec in recs)
    lookup = {node.pk: node for node in nodes}

    for node in lookup.values():
        parent = lookup.get(node.parent_pk)
        if parent:
            node.parent = parent
            parent.children.append(node)

    return [node for node in lookup.values() if not node.parent]


class RequestDAO:
    def __init__(self, db: sqlite3.Connection = None):
        self.db = db or db_local.db

    def get_requests(self, has_collection=True) -> List[RequestTreeNode]:
        rows = self.db.execute(f'''
        select id, collection_id, parent_id, folder_json, request_json 
        from requests
        {'where collection_id is not null' if has_collection else 'where collection_id is null'}
        ''').fetchall()
        rows = (NodeRecord(*row) for row in rows)
        return map_records(rows)

    def save_request(self, node: RequestTreeNode):
        exists = bool(self.db.execute('select count(*) > 0 from requests where id = ?', (node.pk,)).fetchone()[0])

        request_json, folder_json = None, None
        if node.is_folder():
            folder_json = json.dumps(vars(node.folder))
        else:
            request_json = json.dumps(vars(node.request))

        if exists:
            self.db.execute('''
            update requests set collection_id = ?, parent_id = ?, folder_json = ?, request_json = ?
            where id = ?
            ''', (node.collection_pk, node.parent_pk, folder_json, request_json))
        else:
            self.db.execute('''
            insert into requests (id, collection_id, parent_id, folder_json, request_json) values (?, ?, ?, ?, ?)
            ''', (node.pk, node.collection_pk, node.parent_pk, folder_json, request_json))


class CollectionDAO:
    def __init__(self, db: sqlite3.Connection = None, request_dao: RequestDAO = None):
        self.db = db or db_local.db
        self.request_dao = request_dao or RequestDAO(self.db)

    def get_collections(self) -> List[CollectionModel]:
        query = ''' select id, name from collections c '''

        collections = {
            row[0]: CollectionModel(pk=row[0], name=row[1])
            for row in self.db.execute(query).fetchall()
        }

        nodes = self.request_dao.get_requests()
        for node in nodes:
            col = collections[node.collection_pk]
            col.nodes.append(node)

        return list(collections.values())

    def save_collection(self, col: CollectionModel):
        exists = bool(self.db.execute('select count(*) > 0 from collections where id = ?', (col.pk,)).fetchone()[0])
        if exists:
            self.db.execute('update collections set name = ? where id = ?', (col.name, col.pk))
        else:
            self.db.execute('insert into collections (id, name) values (?, ?)', (col.pk, col.name))
