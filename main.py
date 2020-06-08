import logging
from threading import local
from typing import List

import gi

gi.require_version("Gtk", "3.0")
gi.require_version('GtkSource', '4')
gi.require_version('WebKit2', '4.0')  # TODO: Ensure we don't crash if webkit isn't available
from gi.repository import Gtk, GtkSource, Gdk, GLib

from models import RequestModel, MainModel, CollectionModel, RequestTreeNode
from db import CollectionDAO, DB_EXECUTOR
from request_editor import RequestEditor
from request_list import RequestList
from active_request_tab import ActiveRequestTab

logging.basicConfig(
    format='%(asctime)s - %(module)s - [%(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.INFO)

log = logging.getLogger(__name__)


@Gtk.Template.from_file('ui/MainWindow.glade')
class MainWindow(Gtk.Window):
    __gtype_name__ = "MainWindow"

    header_bar: Gtk.HeaderBar = Gtk.Template.Child()
    request_pane: Gtk.Paned = Gtk.Template.Child()
    new_request_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.model = MainModel()
        self.connect('destroy', Gtk.main_quit)
        self.set_icon_from_file('resources/img/nightcap-round-grey-100x100.png')

        self.request_list = RequestList(self)
        self.request_list.set_size_request(200, -1)

        self.new_request_button.connect('clicked', self.on_new_request_clicked)

        self.request_editor = RequestEditor(self)

        # TODO: Scroll wheel to scroll the notebook
        self.active_requests_notebook_box = Gtk.VBox()
        self.active_requests_notebook = Gtk.Notebook()
        self.active_requests_notebook.set_scrollable(True)
        self.active_requests_notebook.set_show_border(False)

        self._add_blank_request(True)
        self.active_requests_notebook_box.pack_start(self.active_requests_notebook, False, False, 0)
        self.active_requests_notebook_box.pack_end(self.request_editor.outer_box, True, True, 0)

        # Don't allow either pane to shrink beyond its minimum size
        self.request_pane.pack1(self.request_list, True, False)
        self.request_pane.pack2(self.active_requests_notebook_box, True, False)

        self.active_requests_notebook.connect('switch-page', self._on_requests_notebook_switch_page)

        self.show_all()
        self.load_collections()

    def _on_requests_notebook_switch_page(self, notebook: Gtk.Notebook, page: Gtk.Widget, page_num: int):
        current_page = self.active_requests_notebook.get_current_page()
        log.debug('Switching active request from %d to %d', current_page, page_num)
        current_req = self.request_editor.get_request()
        self._get_current_active_tab().request_node = current_req
        page = self.active_requests_notebook.get_nth_page(page_num)
        tab: ActiveRequestTab = self.active_requests_notebook.get_tab_label(page)
        self.request_editor.set_request(tab.request_node)

    def _get_active_requests(self) -> List[RequestTreeNode]:
        reqs = []
        for page_num in range(self.active_requests_notebook.get_n_pages()):
            page = self.active_requests_notebook.get_nth_page(page_num)
            tab: ActiveRequestTab = self.active_requests_notebook.get_tab_label(page)
            reqs.append(tab.request_node)

        return reqs

    def _get_current_active_tab(self) -> ActiveRequestTab:
        pn = self.active_requests_notebook.get_current_page()
        page = self.active_requests_notebook.get_nth_page(pn)
        return self.active_requests_notebook.get_tab_label(page)

    def _get_current_active_request(self) -> RequestTreeNode:
        return self._get_current_active_tab().request_node

    def _add_blank_request(self, set_request=False):
        new_node = RequestTreeNode(request=RequestModel(name='New Request'))
        page = Gtk.DrawingArea()
        new_tab = ActiveRequestTab(self, page, new_node)
        page_num = self.active_requests_notebook.append_page(page, new_tab)
        self.active_requests_notebook.show_all()
        if set_request:
            self.request_editor.set_request(new_node)

        self.active_requests_notebook.set_current_page(page_num)

    def close_tab(self, tab: ActiveRequestTab):
        self.active_requests_notebook.remove(tab.page)
        if not self.active_requests_notebook.get_n_pages():
            self._add_blank_request()

    def on_new_request_clicked(self, btn: Gtk.Button):
        log.info('New request clicked')
        self._add_blank_request()

    def _do_load_collections(self):
        # TODO: Handle error
        try:
            cols = CollectionDAO().get_collections()
            GLib.idle_add(self._handle_collections_loaded, cols)
        except Exception as e:
            log.error('Failed to load collections %s', e)

    def _handle_collections_loaded(self, collections: List[CollectionModel]):
        log.info('Successfully loaded collections from disk. %s', collections)

    def load_collections(self):
        log.info('Loading collections from disk.')
        DB_EXECUTOR.submit(self._do_load_collections)

    def update_active_request(self, node: RequestTreeNode):
        current_req = self.request_editor.get_request()
        self.model.requests[current_req.pk] = current_req
        self.request_editor.set_request(node)

        if current_req.collection_pk:
            self.request_list.update_request(current_req)
            self.request_list.set_active_request(node)
        
        
def create_non_gtk_widgets():
    sv = GtkSource.View()
    sv.destroy()


# Can we do this during install?
def create_user_dirs():
    log.info('Ensuring data directories exist.')


# TODO: Loading screen for starting db, creating user dirs etc?


if __name__ == '__main__':
    create_user_dirs()
    log.info('Bootstrapping gtk resources.')
    create_non_gtk_widgets()

    css_provider = Gtk.CssProvider()
    css_provider.load_from_path('ui/style.css')

    Gtk.StyleContext().add_provider_for_screen(
        Gdk.Screen().get_default(),
        css_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    MainWindow()
    log.info('Starting application.')
    Gtk.main()
