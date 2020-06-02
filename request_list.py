from gi.repository import Gtk

from models import Request


class RequestList:
    def __init__(self):
        builder = Gtk.Builder().new_from_file('ui/RequestList.glade')
        self.tree_view: Gtk.TreeView = builder.get_object('treeView')
        self.request_url_column: Gtk.TreeViewColumn = builder.get_object('requestUrlColumn')
        self.request_url_column_render: Gtk.CellRendererText = builder.get_object('requestUrlColumnRender')
        self.store = Gtk.ListStore(str)
        self.tree_view.set_model(self.store)

    def add_new_request(self, req=None):
        req = req or Request('', '')

        self.store.append([req.name or f'{req.method} - {req.url}'])
