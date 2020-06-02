import gi
gi.require_version("Gtk", "3.0")

import logging
from models import Request
from request_editor import RequestEditor
from request_list import RequestList
from gi.repository import Gtk


logging.basicConfig(
    format='%(asctime)s - %(module)s - [%(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.INFO)

log = logging.getLogger(__name__)


class MainWindow:
    def __init__(self):
        builder = Gtk.Builder().new_from_file('ui/MainWindow.glade')
        self.win: Gtk.Window = builder.get_object('MainWindow')
        self.win.connect('destroy', Gtk.main_quit)

        self.header_bar: Gtk.HeaderBar = builder.get_object('headerBar')
        self.request_pane: Gtk.Paned = builder.get_object('requestPane')
        self.new_request_button: Gtk.Button = builder.get_object('newRequestButton')

        self.request_list = RequestList()

        self.new_request_button.connect('clicked', self.on_new_request_clicked)

        self.request_editor = RequestEditor()
        self.request_pane.add1(self.request_list.tree_view)
        self.request_pane.add2(self.request_editor.outer_box)

        self.win.show_all()

    def on_new_request_clicked(self, btn: Gtk.Button):
        self.request_list.add_new_request(Request('', '', 'New Request'))


if __name__ == '__main__':
    log.info('Bootstrapping gtk resources.')
    MainWindow()
    log.info('Starting application.')
    Gtk.main()
