import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
import logging
from models import RequestModel, MainModel
from request_editor import RequestEditor
from request_list import RequestList


logging.basicConfig(
    format='%(asctime)s - %(module)s - [%(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.INFO)

log = logging.getLogger(__name__)


class MainWindow:
    def __init__(self):
        self.model = MainModel()
        builder = Gtk.Builder().new_from_file('ui/MainWindow.glade')
        self.win: Gtk.Window = builder.get_object('MainWindow')
        self.win.connect('destroy', Gtk.main_quit)

        self.header_bar: Gtk.HeaderBar = builder.get_object('headerBar')
        self.request_pane: Gtk.Paned = builder.get_object('requestPane')
        self.new_request_button: Gtk.Button = builder.get_object('newRequestButton')

        self.request_list = RequestList(self)

        self.new_request_button.connect('clicked', self.on_new_request_clicked)

        self.request_editor = RequestEditor(self)
        self.request_pane.add1(self.request_list.tree_view)
        self.request_pane.add2(self.request_editor.outer_box)

        self.win.show_all()

        self.load_requests()

    def on_new_request_clicked(self, btn: Gtk.Button):
        req = RequestModel(name='New Request')
        log.info('Created new request: %s', req.pk)
        self.request_list.add_new_request(req)
        self.update_active_request(req)

    def load_requests(self):
        req = RequestModel(name='New Request', url='http://localhost:5000')
        self.model.requests = {req.pk: req}
        self.request_editor.set_request(req)
        self.request_list.set_requests(self.model.requests)

    def update_active_request(self, req: RequestModel):
        current_req = self.request_editor.get_request()
        self.model.requests[current_req.pk] = current_req
        self.request_editor.set_request(req)
        self.request_list.update_request(current_req)
        self.request_list.set_active_request(req)


if __name__ == '__main__':
    log.info('Bootstrapping gtk resources.')
    MainWindow()
    log.info('Starting application.')
    Gtk.main()
