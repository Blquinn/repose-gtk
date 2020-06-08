from typing import List, Tuple

from gi.repository import Gtk


@Gtk.Template.from_file('ui/ParamTable.glade')
class ParamTable(Gtk.TreeView):
    __gtype_name__ = 'ParamTable'

    key_column: Gtk.TreeViewColumn = Gtk.Template.Child()
    key_column_renderer: Gtk.CellRendererText = Gtk.Template.Child()
    value_column: Gtk.TreeViewColumn = Gtk.Template.Child()
    value_column_renderer: Gtk.CellRendererText = Gtk.Template.Child()
    description_column: Gtk.TreeViewColumn = Gtk.Template.Child()
    description_column_renderer: Gtk.CellRendererText = Gtk.Template.Child()

    def __init__(self):
        super(ParamTable, self).__init__()
        self.store = Gtk.ListStore(str, str, str)  # (key, value, description)
        self.set_model(self.store)
        self.add_row()

    def add_row(self, row: Tuple[str, str, str] = None):
        self.store.append(row or ('', '', ''))

    def prepend_row(self, row: Tuple[str, str, str] = None):
        self.store.prepend(row or ('', '', ''))

    def prepend_or_update_row_by_key(self, row: Tuple[str, str, str]):
        key, val, desc = row
        for store_row in self.store:
            if store_row[0].lower() == key.lower():
                store_row[1] = val
                store_row[2] = desc
                return
        self.prepend_row(row)

    def delete_row_by_key(self, key: str):
        lk = key.lower()
        idx = None
        for i, row in enumerate(self.store):
            if row[0].lower() == lk:
                idx = i
                break

        if idx is not None:
            self.store.remove(self.store[idx].iter)

    @Gtk.Template.Callback('on_key_column_renderer_edited')
    def _on_key_column_edited(self, widget: Gtk.Widget, path: Gtk.TreePath, text: str):
        self.store[path][0] = text

        if text and len(self.store) and len(self.store[-1][0]):
            self.add_row()

    @Gtk.Template.Callback('on_value_column_renderer_edited')
    def _on_value_column_edited(self, widget: Gtk.Widget, path: Gtk.TreePath, text: str):
        self.store[path][1] = text

    @Gtk.Template.Callback('on_description_column_renderer_edited')
    def _on_description_column_edited(self, widget: Gtk.Widget, path: Gtk.TreePath, text: str):
        self.store[path][2] = text

    def get_values(self) -> List[Tuple[str, str, str]]:
        return [(row[0], row[1], row[2]) for row in self.store if row[0]]

    def set_values(self, rows: List[Tuple[str, str, str]]):
        self.store.clear()
        for row in rows or [('', '', '')]:
            self.store.append(row)
