from uuid import uuid1
from typing import Dict, List, Tuple, Optional


class MainModel:
    def __init__(self):
        self.requests: Dict[str, RequestTreeNode] = {}


class RequestModel:
    def __init__(self,
                 url: str = '',
                 method: str = 'GET',
                 name: str = '',
                 request_body: str = '',
                 params: List[Tuple[str, str, str]] = None,
                 request_headers: List[Tuple[str, str, str]] = None,
                 saved: bool = False,
                 ):
        self.url = url
        self.method = method
        self.name = name
        self.params = params or [('', '', '')]
        self.request_body = request_body
        self.request_headers = request_headers or [('', '', '')]
        self.saved = saved


class FolderModel:
    def __init__(self, name: str):
        self.name = name


class RequestTreeNode:
    def __init__(self,
                 parent_pk: str = None,
                 collection_pk: str = None,
                 pk: str = None,
                 parent=None,
                 collection=None,
                 request: Optional[RequestModel] = None,
                 folder: Optional[FolderModel] = None
                 ):
        assert request or folder

        self.pk = pk or str(uuid1())
        self.parent_pk = parent_pk
        self.parent = parent
        self.collection_pk = collection.pk if collection else collection_pk
        self.collection = collection
        self.folder = folder
        self.request = request
        self.children = []

    def is_folder(self) -> bool:
        return self.folder is not None

    def add_child(self, node):
        assert self.is_folder()
        node.parent = self
        node.parent_pk = self.pk
        self.children.append(node)

    def remove_request(self, node):
        self.children.remove(node)


class CollectionModel:
    def __init__(self, name: str, nodes: List[RequestTreeNode] = None, pk: str = None):
        self.pk = pk or str(uuid1())
        self.name = name
        self.nodes = nodes or []

    def add_node(self, node: RequestTreeNode):
        node.collection = self
        node.collection_pk = self.pk
        self.nodes.append(node)
