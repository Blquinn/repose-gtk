import logging
from typing import Dict

from gi.repository import Gtk

from widgets.collection import Collection
from models import RequestModel, CollectionModel, RequestTreeNode, FolderModel

log = logging.getLogger(__name__)


@Gtk.Template.from_file('ui/RequestList.glade')
class RequestList(Gtk.ListBox):
    __gtype_name__ = "RequestList"

    def __init__(self, main_window):
        super(RequestList, self).__init__()
        self.main_window = main_window

        col1 = CollectionModel('My collection')
        col1.add_node(RequestTreeNode(collection=col1, parent_pk=None, request=RequestModel(name='Request two')))
        dir_1 = RequestTreeNode(None, collection=col1, folder=FolderModel('Dir1'))
        dir_1.add_child(
            RequestTreeNode(collection=col1, parent_pk=dir_1.pk, request=RequestModel(name='Dir1 Request1')))
        dir_1.add_child(
            RequestTreeNode(collection=col1, parent_pk=dir_1.pk, request=RequestModel(name='Dir1 Request2')))
        col1.add_node(dir_1)
        self.add(Collection(col1))

    def set_requests(self, requests: Dict[str, RequestModel]):
        self.request_list = requests
        for req in requests.values():
            self._append_request(req)

    def _append_request(self, node: RequestTreeNode):
        assert not node.is_folder()
        req = node.request
        self.store.append([req.name or f'{req.method} - {req.url}', node.pk])

    def add_new_request(self, req=None):
        req = req or RequestModel('', '')
        self.request_list[req.pk] = req
        self._append_request(req)

    def on_row_activated(self, tree: Gtk.TreeView, path: Gtk.TreePath, col: Gtk.TreeViewColumn):
        it = self.store.get_iter(path)
        request_name = self.store.get_value(it, 0)
        request_pk = self.store.get_value(it, 1)
        log.info('Selected %s - %s', request_name, request_pk)
        node = self.request_list[request_pk]
        self.main_window.update_active_request(node)

    def set_active_request(self, req: RequestTreeNode):
        for idx, (name, pk) in enumerate(self.store):
            if pk == req.pk:
                self.tree_view.set_cursor(Gtk.TreePath(idx))
                break

    def update_request(self, req: RequestTreeNode):
        assert req.collection_pk

        # Update the request name
        # for child in self.get_children():
        # for idx, (name, pk) in enumerate(self.store):
        #     if pk == req.pk:
        #         if req.is_folder():
        #             self.store[idx][0] = req.folder.name
        #         else:
        #             self.store[idx][0] = req.request.name
        #         break
