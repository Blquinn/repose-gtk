from typing import List, Tuple

from gi.repository import Gtk


class ParamTable:
    def __init__(self):
        builder = Gtk.Builder().new_from_file('ui/ParamTable.glade')
        self.table: Gtk.TreeView = builder.get_object('ParamTable')
        self.key_column: Gtk.TreeViewColumn = builder.get_object('keyColumn')
        self.key_column_renderer: Gtk.CellRendererText = builder.get_object('keyRenderer')
        self.value_column: Gtk.TreeViewColumn = builder.get_object('valueColumn')
        self.value_column_renderer: Gtk.CellRendererText = builder.get_object('valueRenderer')
        self.description_column: Gtk.TreeViewColumn = builder.get_object('descriptionColumn')
        self.description_column_renderer: Gtk.CellRendererText = builder.get_object('descriptionRenderer')

        self.store = Gtk.ListStore(str, str, str)  # (key, value, description)
        self.table.set_model(self.store)
        self.add_row()

        # Connections

        self.key_column_renderer.connect('edited', self.on_key_column_edited)
        self.value_column_renderer.connect('edited', self.on_value_column_edited)
        self.description_column_renderer.connect('edited', self.on_description_column_edited)

    def add_row(self):
        self.store.append(['', '', ''])

    def on_key_column_edited(self, widget: Gtk.Widget, path: Gtk.TreePath, text: str):
        self.store[path][0] = text

        if text and len(self.store) and len(self.store[-1][0]):
            self.add_row()

    def on_value_column_edited(self, widget: Gtk.Widget, path: Gtk.TreePath, text: str):
        self.store[path][1] = text

    def on_description_column_edited(self, widget: Gtk.Widget, path: Gtk.TreePath, text: str):
        self.store[path][2] = text

    def get_values(self) -> List[Tuple[str, str]]:
        return [(row[0], row[1]) for row in self.store if row[0]]
