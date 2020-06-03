import json
import logging
from datetime import timedelta
from typing import List, Tuple, Dict, Optional

import requests
from gi.repository import Gtk, GLib

from models import RequestModel
from pool import TPE
from param_table import ParamTable

log = logging.getLogger(__name__)


def sizeof_fmt(num: float, suffix='B') -> str:
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Y', suffix)


def timedelta_fmt(delta: timedelta) -> str:
    ts = delta.total_seconds()

    if ts >= 1:
        for unit in ['s', 'M', 'H']:
            if abs(ts) < 60:
                return '%3.1f %s' % (ts, unit)
            ts /= 60
    else:
        mcs = delta.microseconds
        for unit in ['μs', 'ms']:
            if mcs < 1000:
                return '%d %s' % (mcs, unit)
            mcs /= 1000

    return str(delta)


def format_response_size(response: requests.Response) -> str:
    cl = response.headers.get('content-length')
    if cl:
        return sizeof_fmt(float(cl))
    return sizeof_fmt(float(len(response.content)))


class RequestEditor:
    def __init__(self):
        self.active_request: Optional[RequestModel] = None
        builder = Gtk.Builder().new_from_file('ui/RequestEditor.glade')
        self.outer_box: Gtk.Box = builder.get_object('outerBox')

        self.request_method_combo: Gtk.ComboBox = builder.get_object('requestMethodCombo')
        self.request_method_combo_store: Gtk.ListStore = builder.get_object('requestMethodComboStore')

        self.request_name_entry: Gtk.Entry = builder.get_object('requestNameEntry')
        self.url_entry: Gtk.Entry = builder.get_object('urlEntry')
        self.send_button: Gtk.Button = builder.get_object('sendButton')
        self.save_button: Gtk.Button = builder.get_object('saveButton')

        self.request_response_notebook: Gtk.Notebook = builder.get_object('requestResponseNotebook')
        self.request_notebook: Gtk.Notebook = builder.get_object('requestNotebook')
        self.request_text: Gtk.TextView = builder.get_object('requestText')

        self.response_notebook: Gtk.Notebook = builder.get_object('responseNotebook')
        self.response_text_overlay: Gtk.Overlay = builder.get_object('responseTextOverlay')
        self.response_text: Gtk.TextView = builder.get_object('responseText')
        self.response_loading_spinner: Gtk.Spinner = builder.get_object('responseLoadingSpinner')
        self.response_headers_text: Gtk.TextView = builder.get_object('responseHeadersText')
        self.response_status_label: Gtk.Label = builder.get_object('responseStatusLabel')
        self.response_time_label: Gtk.Label = builder.get_object('responseTimeLabel')
        self.response_size_label: Gtk.Label = builder.get_object('responseSizeLabel')

        self.param_table = ParamTable()
        self.request_header_table = ParamTable()
        self.request_notebook.insert_page(self.param_table.table, Gtk.Label(label='Params'), 0)
        self.request_notebook.insert_page(self.request_header_table.table, Gtk.Label(label='Headers'), 1)
        self.request_notebook.set_current_page(0)

        # Connections

        self.send_button.connect('clicked', self.on_send_pressed)
        self.save_button.connect('clicked', self.on_save_pressed)

        # TODO: Remove me
        self.url_entry.set_text('http://localhost:4444')

    def get_request(self) -> RequestModel:
        req = self.active_request
        req.url = self.url_entry.get_text()
        req.method = self.get_method()
        req.request_body = self.get_request_text()
        req.request_headers = self.request_header_table.get_values()
        req.params = self.param_table.get_values()
        req.name = self.request_name_entry.get_text()
        return req

    def set_request(self, req: RequestModel):
        self.active_request = req
        self.url_entry.set_text(req.url)
        self.set_method(req.method)
        self.request_text.get_buffer().set_text(req.request_body, -1)
        self.request_header_table.set_values(req.request_headers)
        self.param_table.set_values(req.params)
        self.request_name_entry.set_text(req.name)

    def get_request_text(self) -> str:
        buf: Gtk.TextBuffer = self.request_text.get_buffer()
        start, end = buf.get_bounds()
        return buf.get_text(start, end, True)

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
        url = self.url_entry.get_text()
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url

        meth_idx = self.request_method_combo.get_active()
        meth = self.request_method_combo_store[meth_idx][0]

        self.set_response_spinner_active(True)
        self.request_response_notebook.set_current_page(1)  # Response page

        params = [(k, v) for k, v, _ in self.param_table.get_values()]
        headers = dict([(k, v) for k, v, _ in self.request_header_table.get_values()])
        body = self.get_request_text()

        TPE.submit(self.do_request, meth, url, params, headers, body)
        log.info('Creating request to %s - %s', meth, url)

    def do_request(self, method: str, url: str, params: List[Tuple[str, str]], headers: Dict[str, str], data=None):
        try:
            res = requests.request(method, url, params=params, headers=headers, data=data)
            GLib.idle_add(self.handle_request_finished, res)
        except Exception as e:
            GLib.idle_add(self.handle_request_finished_exceptionally, e)

    def handle_request_finished(self, response: requests.Response):
        log.info('Got %s response from %s', response.status_code, self.url_entry.get_text())
        try:
            ct = response.headers.get('content-type')
            if ct == 'application/json':
                j = response.json()
                txt = json.dumps(j, indent=2)
            elif not response.text:
                txt = 'Empty Response'
            else:
                txt = response.text

            # self.response_status_label.set_markup()
            status_markup = f'{response.status_code} {response.reason}'
            if not response.ok:
                status_markup = f'<span foreground="red">{status_markup}</span>'

            self.response_status_label.set_markup(f'Status: {status_markup}')
            self.response_time_label.set_text(f'Time: {timedelta_fmt(response.elapsed)}')
            self.response_size_label.set_text(f'Size: {format_response_size(response)}')

            # Write headers
            headers_markup = '\n'.join([f'<b>{k}</b> → {v}' for k, v in response.headers.items()])
            buf: Gtk.TextBuffer = self.response_headers_text.get_buffer()
            start, end = buf.get_bounds()
            buf.delete(start, end)
            buf.insert_markup(buf.get_start_iter(), headers_markup, -1)

            self.response_text.get_buffer().set_text(txt)
            self.response_notebook.set_current_page(1)  # Body page
        finally:
            self.set_response_spinner_active(False)

    def handle_request_finished_exceptionally(self, ex: Exception):
        self.set_response_spinner_active(False)
        self.response_text.get_buffer().set_text(f'Error occurred while performing request: {ex}')
        self.response_notebook.set_current_page(1)  # Body page

    def set_response_spinner_active(self, active: bool):
        if active:
            self.response_loading_spinner.start()
            self.response_text_overlay.reorder_overlay(self.response_loading_spinner, 1)
        else:
            self.response_loading_spinner.stop()
            self.response_text_overlay.reorder_overlay(self.response_loading_spinner, 0)
