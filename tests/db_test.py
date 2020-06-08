import pathlib
import unittest

from db import RequestDAO, CollectionDAO, get_connection
from models import RequestModel, CollectionModel, RequestTreeNode, FolderModel

TEST_DB_PATH = '/tmp/repose_test.db'


class RequestDAOTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = get_connection(TEST_DB_PATH)
        self.request_dao = RequestDAO(self.db)
        self.collection_dao = CollectionDAO(self.db, self.request_dao)

    def tearDown(self) -> None:
        pathlib.Path(TEST_DB_PATH).unlink()

    def test_saving_collection(self):
        test_col = CollectionModel('Test collection')
        self.collection_dao.save_collection(test_col)

        req1 = RequestTreeNode(None, test_col.pk, request=RequestModel(name='req1', url='http://foo.com'))
        self.request_dao.save_request(req1)
        req2 = RequestTreeNode(None, test_col.pk, request=RequestModel(name='req2', url='http://foo.com'))
        self.request_dao.save_request(req2)

        dir1 = RequestTreeNode(None, test_col.pk, folder=FolderModel('dir1'))
        self.request_dao.save_request(dir1)

        req3 = RequestTreeNode(None, test_col.pk, request=RequestModel(name='dir1 req1', url='http://foo.com'))
        dir1.add_child(req3)
        self.request_dao.save_request(req3)

        all_cols = self.collection_dao.get_collections()
        self.assertEqual(1, len(all_cols))
        first_col = all_cols[0]
        self.assertEqual(test_col.name, first_col.name)
        self.assertEqual(3, len(first_col.nodes))
        self.assertEqual(None, first_col.nodes[0].parent_pk)
        self.assertEqual(0, len(first_col.nodes[0].children))
        self.assertEqual(1, len(first_col.nodes[2].children))
        self.assertEqual('dir1 req1', first_col.nodes[2].children[0].request.name)


if __name__ == '__main__':
    unittest.main()
