import json
from typing import List

from config import DATA_DIR
import sqlite3

from models import RequestModel


class RequestDAO:
    def __init__(self):
        self.db = sqlite3.connect(f'{DATA_DIR}/storage.db', 30.0)
        try:
            self.db.execute("""
            create table requests (
                id text primary key,
                request_json text 
            );
            """)
        except sqlite3.OperationalError:
            pass

    def get_requests(self) -> List[RequestModel]:
        cur = self.db.execute('select id, request_json from requests')
        rows = cur.fetchmany()
        return [RequestModel(pk=row[0], **json.loads(row[1])) for row in rows]

    def save_request(self, request: RequestModel):
        exists = bool(self.db.execute('select count(*) > 0 from requests where id = ?', (request.pk,)).fetchone()[0])
        dic = vars(request).copy()
        dic.pop('pk')
        request_json = json.dumps(dic)
        if exists:
            self.db.execute('update requests set request_json = ? where id = ?', (request_json, request.pk))
        else:
            self.db.execute('insert into requests (id, request_json) values (?, ?)', (request.pk, request_json))
