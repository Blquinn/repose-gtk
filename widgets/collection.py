import logging

from gi.repository import Gtk

from models import CollectionModel, RequestTreeNode

log = logging.getLogger(__name__)


@Gtk.Template.from_file("ui/Collection.glade")
class Collection(Gtk.Box):
    __gtype_name__ = "Collection"

    folder_icon = Gtk.Image().new_from_icon_name('folder', 50)

    collection_header_event_box: Gtk.EventBox = Gtk.Template.Child()
    collection_name_label: Gtk.Label = Gtk.Template.Child()
    collection_revealer: Gtk.Revealer = Gtk.Template.Child()
    requests_tree_view: Gtk.TreeView = Gtk.Template.Child()
    requests_tree_store: Gtk.TreeStore = Gtk.Template.Child()
    request_name_column: Gtk.TreeViewColumn = Gtk.Template.Child()

    def __init__(self, model: CollectionModel):
        super(Collection, self).__init__()
        self.model = model
        self.collection_name_label.set_text(model.name)
        self.populate_collection()

    @Gtk.Template.Callback('tree_view_row_activated')
    def _tree_view_row_activated(self, view: Gtk.TreeView, path: Gtk.TreePath, col: Gtk.TreeViewColumn):
        it = self.requests_tree_store.get_iter(path)
        req_pk = self.requests_tree_store.get_value(it, 1)
        log.info('')
        # print(view, path, col)

    @Gtk.Template.Callback()
    def name_label_pressed(self, *args):
        self.collection_revealer.set_reveal_child(not self.collection_revealer.get_reveal_child())

    def populate_collection(self):
        it: Gtk.TreeIter = self.requests_tree_store.get_iter_first()
        for node in self.model.nodes:
            self.add_request_node(it, node)

    def add_request_node(self, it: Gtk.TreeIter, node: RequestTreeNode):
        if node.is_folder():
            parent_it = self.requests_tree_store.append(it, [node.folder.name, node.pk, None])
        else:
            parent_it = self.requests_tree_store.append(it, [node.request.name, node.pk, None])

        for child in node.children:
            self.add_request_node(parent_it, child)
