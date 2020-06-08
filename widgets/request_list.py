import logging
from typing import List

from gi.repository import Gtk

from models import CollectionModel, RequestTreeNode
from widgets.collection import Collection

log = logging.getLogger(__name__)


@Gtk.Template.from_file('ui/RequestList.glade')
class RequestList(Gtk.ListBox):
    __gtype_name__ = "RequestList"

    def __init__(self, main_window):
        super(RequestList, self).__init__()
        self.main_window = main_window

    def load_collections(self, collections: List[CollectionModel]):
        for col in collections:
            self.add(Collection(col))

    def set_active_request(self, req: RequestTreeNode):
        for idx, (name, pk) in enumerate(self.store):
            if pk == req.pk:
                self.tree_view.set_cursor(Gtk.TreePath(idx))
                break

    def update_request(self, req: RequestTreeNode):
        assert req.collection_pk
