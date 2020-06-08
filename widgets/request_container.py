import logging
from typing import Tuple, List, Dict

from gi.repository import Gtk, GtkSource

from models import RequestTreeNode
from widgets.param_table import ParamTable
from utils import language_map, content_type_map

log = logging.getLogger(__name__)


class RequestContainer:
    def __init__(self, request_editor):
        self.request_editor = request_editor
        builder = Gtk.Builder().new_from_file('ui/RequestContainer.glade')

        self.request_notebook: Gtk.Notebook = builder.get_object('requestNotebook')
        self.lang_manager = GtkSource.LanguageManager()
        self.request_text: GtkSource.View = builder.get_object('requestText')

        style_manager = GtkSource.StyleSchemeManager()
        scheme: GtkSource.StyleScheme = style_manager.get_scheme('kate')
        self.request_text.get_buffer().set_style_scheme(scheme)

        # Set based on type of request
        lang = self.lang_manager.get_language('text')
        self.request_text.get_buffer().set_language(lang)

        self.request_type_notebook: Gtk.Notebook = builder.get_object('requestTypeNotebook')
        self.request_form_data = ParamTable()
        self.request_type_notebook.insert_page(self.request_form_data.table, Gtk.Label('Form Data'), 2)
        self.request_form_urlencoded = ParamTable()
        self.request_type_notebook.insert_page(self.request_form_urlencoded.table, Gtk.Label('Form Url-Encoded'), 3)

        self.request_type_popover: Gtk.Popover = builder.get_object('requestTypePopover')
        self.request_type_popover_tree_view: Gtk.TreeView = builder.get_object('requestTypePopoverTreeView')
        self.request_type_popover_tree_view_store: Gtk.ListStore = builder.get_object('requestTypePopoverStore')

        self.param_table = ParamTable()
        self.request_header_table = ParamTable()
        self.request_notebook.insert_page(self.param_table.table, Gtk.Label(label='Params'), 0)
        self.request_notebook.insert_page(self.request_header_table.table, Gtk.Label(label='Headers'), 1)
        self.request_notebook.set_current_page(0)

        # Connections

        self.request_type_popover_tree_view.connect('row-activated', self._on_popover_row_activated)
        self.request_type_notebook.connect('switch-page', self._on_request_type_notebook_page_switched)

    def _on_request_type_notebook_page_switched(self, notebook: Gtk.Notebook, page: Gtk.Widget, page_num: int):
        # Update the content type
        ct_func = {
            1: self._get_active_content_type,
            2: lambda: 'multipart/form-data',
            3: lambda: 'application/x-www-form-urlencoded',
        }.get(page_num)

        if not ct_func:
            self.request_header_table.delete_row_by_key('content-type')
            return

        self.request_header_table.prepend_or_update_row_by_key(
            ('Content-Type', ct_func(), ''))

    def _get_active_content_type(self):
        sel: Gtk.TreeSelection = self.request_type_popover_tree_view.get_selection()
        model, paths = sel.get_selected_rows()
        if paths:
            type_id = model[paths[0]][1]
            return content_type_map[type_id]

        return 'text/plain'

    def _on_popover_row_activated(self, tree: Gtk.TreeView, path: Gtk.TreePath, col: Gtk.TreeViewColumn):
        store = self.request_type_popover_tree_view_store
        it = store.get_iter(path)
        type_name = store.get_value(it, 0)
        type_id = store.get_value(it, 1)
        log.info('Selected request type %s - %s', type_id, type_name)

        lang = self.lang_manager.get_language(language_map.get(type_id, 'text'))
        self.request_text.get_buffer().set_language(lang)

        if type_id == 'text':
            self.request_header_table.delete_row_by_key('content-type')
        else:
            self.request_header_table.prepend_or_update_row_by_key(('Content-Type', content_type_map[type_id], ''))

        self.request_type_popover.hide()
        self.request_type_notebook.set_current_page(1)

    def get_request_text(self) -> str:
        buf: Gtk.TextBuffer = self.request_text.get_buffer()
        start, end = buf.get_bounds()
        return buf.get_text(start, end, True)

    def get_body(self):
        page = self.request_type_notebook.get_current_page()
        return {
            0: lambda: None,
            1: self.get_request_text,
            2: self._get_form_data,
            3: self._get_urlencoded_data,
            4: self._get_binary_data
        }[page]()

    def _get_form_data(self):
        return [(k, v) for k, v, _, in self.request_form_data.get_values()]

    def _get_urlencoded_data(self):
        return [(k, v) for k, v, _, in self.request_form_urlencoded.get_values()]

    def _get_binary_data(self):
        raise NotImplemented

    def set_request(self, node: RequestTreeNode):
        req = node.request
        self.request_text.get_buffer().set_text(req.request_body, -1)
        self.request_header_table.set_values(req.request_headers)
        self.param_table.set_values(req.params)

    def get_request(self, node: RequestTreeNode):
        req = node.request
        req.request_body = self.get_request_text()
        req.request_headers = self.request_header_table.get_values()
        req.params = self.param_table.get_values()

    def get_params(self) -> List[Tuple[str, str]]:
        return [(k, v) for k, v, _ in self.param_table.get_values()]

    def get_headers(self) -> Dict[str, str]:
        return dict([(k, v) for k, v, _ in self.request_header_table.get_values()])
