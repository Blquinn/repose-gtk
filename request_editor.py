import logging
from typing import List, Tuple, Dict, Optional

import requests
from gi.repository import Gtk, GLib

from models import RequestModel
from pool import TPE
from request_container import RequestContainer
from response_container import ResponseContainer

log = logging.getLogger(__name__)


class RequestEditor:
    def __init__(self, main_window):
        self.main_window = main_window
        self.active_request: Optional[RequestModel] = None
        self.last_response: Optional[requests.Response] = None

        builder: Gtk.Builder = Gtk.Builder().new_from_file('ui/RequestEditor.glade')
        self.outer_box: Gtk.Box = builder.get_object('outerBox')

        self.request_method_combo: Gtk.ComboBox = builder.get_object('requestMethodCombo')
        self.request_method_combo_store: Gtk.ListStore = builder.get_object('requestMethodComboStore')

        self.request_name_entry: Gtk.Entry = builder.get_object('requestNameEntry')
        self.url_entry: Gtk.Entry = builder.get_object('urlEntry')
        self.send_button: Gtk.Button = builder.get_object('sendButton')
        self.save_button: Gtk.Button = builder.get_object('saveButton')

        self.request_response_stack_switcher: Gtk.StackSwitcher = builder.get_object('requestResponseStackSwitcher')
        self.request_response_stack: Gtk.Stack = builder.get_object('requestResponseStack')

        self.request_container = RequestContainer(self)
        self.request_response_stack.add_titled(self.request_container.request_notebook, 'Request', 'Request')

        self.response_container = ResponseContainer(self)
        self.request_response_stack.add_titled(self.response_container.response_text_overlay, 'Response', 'Response')

        # Connections

        self.request_name_entry.connect('activate', self._on_request_name_changed)
        self.send_button.connect('clicked', self.on_send_pressed)
        self.save_button.connect('clicked', self.on_save_pressed)

    def _on_request_name_changed(self, entry: Gtk.Entry):
        self.active_request = self.get_request()
        self.main_window.request_list.update_request(self.active_request)

    def get_request(self) -> RequestModel:
        req = self.active_request
        self.request_container.get_request(req)
        req.url = self.url_entry.get_text()
        req.method = self.get_method()
        req.name = self.request_name_entry.get_text()
        return req

    def set_request(self, req: RequestModel):
        self.active_request = req
        self.url_entry.set_text(req.url)
        self.set_method(req.method)
        self.request_name_entry.set_text(req.name)
        self.request_container.set_request(req)

    def set_method(self, method: str):
        it = self.request_method_combo_store.get_iter_first()
        meth_idx = next((idx for idx, row in enumerate(self.request_method_combo_store[it]) if row[0] == method), 0)
        self.request_method_combo.set_active(meth_idx)

    def get_method(self) -> str:
        idx = self.request_method_combo.get_active()
        return self.request_method_combo_store[idx][0]

    def on_save_pressed(self, btn):
        log.info('Save pressed')

    def on_send_pressed(self, btn):
        url = self._format_request_url()
        meth_idx = self.request_method_combo.get_active()
        meth = self.request_method_combo_store[meth_idx][0]

        self.response_container.set_response_spinner_active(True)
        self.request_response_stack.set_visible_child(self.response_container.response_text_overlay)

        params = self.request_container.get_params()
        headers = self.request_container.get_headers()
        body = self.request_container.get_body()

        TPE.submit(self.do_request, meth, url, params, headers, body)
        log.info('Creating request to %s - %s', meth, url)

    def do_request(self, method: str, url: str, params: List[Tuple[str, str]], headers: Dict[str, str], data=None):
        try:
            if type(data) is str:
                data = data.encode('utf-8')

            res = requests.request(method, url, params=params, headers=headers, data=data)
            # TODO: Load all the data into custom object before sending it back to UI thread
            GLib.idle_add(self.handle_request_finished, res)
        except Exception as e:
            log.error('Error occurred while sending request %s', e)
            GLib.idle_add(self.response_container.handle_request_finished_exceptionally, e)

    def handle_request_finished(self, response: requests.Response):
        log.info('Got %s response from %s', response.status_code, self.url_entry.get_text())
        self.last_response = response
        self.response_container.handle_request_finished(response)

    def _format_request_url(self) -> str:
        url = self.url_entry.get_text()
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url
        return url
