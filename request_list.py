import logging
from typing import Dict, Optional
from gi.repository import Gtk

from models import RequestModel

log = logging.getLogger(__name__)


class RequestList:
    def __init__(self, main_window):
        self.main_window = main_window
        self.request_list: Optional[Dict[str, RequestModel]] = None
        builder = Gtk.Builder().new_from_file('ui/RequestList.glade')
        self.tree_view: Gtk.TreeView = builder.get_object('treeView')
        self.request_url_column: Gtk.TreeViewColumn = builder.get_object('requestUrlColumn')
        self.request_url_column_render: Gtk.CellRendererText = builder.get_object('requestUrlColumnRender')
        self.store = Gtk.ListStore(str, str)  # (name, id)
        self.tree_view.set_model(self.store)

        # Connections

        self.tree_view.connect('row-activated', self.on_row_activated)

    def set_requests(self, requests: Dict[str, RequestModel]):
        self.request_list = requests
        for req in requests.values():
            self._append_request(req)

    def _append_request(self, req):
        self.store.append([req.name or f'{req.method} - {req.url}', req.pk])

    def add_new_request(self, req=None):
        req = req or RequestModel('', '')
        self.request_list[req.pk] = req
        self._append_request(req)

    def on_row_activated(self, tree: Gtk.TreeView, path: Gtk.TreePath, col: Gtk.TreeViewColumn):
        it = self.store.get_iter(path)
        request_name = self.store.get_value(it, 0)
        request_pk = self.store.get_value(it, 1)
        log.info('Selected %s - %s', request_name, request_pk)
        req = self.request_list[request_pk]
        self.main_window.update_active_request(req)

    def set_active_request(self, req: RequestModel):
        for idx, (name, pk) in enumerate(self.store):
            if pk == req.pk:
                self.tree_view.set_cursor(Gtk.TreePath(idx))
                break

    def update_request(self, req: RequestModel):
        # Update the request name
        for idx, (name, pk) in enumerate(self.store):
            if pk == req.pk:
                self.store[idx][0] = req.name
                break

