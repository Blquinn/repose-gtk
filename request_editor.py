import json
import logging
from datetime import timedelta
from typing import List, Tuple, Dict, Optional

from gi.repository import Gtk, GLib, GtkSource, WebKit2
from lxml import etree, html
import requests

from models import RequestModel
from pool import TPE
from param_table import ParamTable
import jsonpath_rw

log = logging.getLogger(__name__)


language_map = {
    'text': 'text',
    'text-plain': 'text',
    'json': 'json',
    'js': 'js',
    'xml-application': 'xml',
    'xml-text': 'xml',
    'html': 'html',
}

content_type_map = {
    'text-plain': 'text/plain',
    'json': 'application/json',
    'js': 'application/javascript',
    'xml-application': 'application/xml',
    'xml-text': 'text/xml',
    'html': 'text/html',
}
content_type_map_reverse = {v: k for k, v in content_type_map.items()}


def parse_content_type(content_type_header: str) -> str:
    return content_type_header.split(';')[0]


def get_content_type(response: requests.Response) -> str:
    return parse_content_type(response.headers.get('content-type', ''))


def get_language_for_mime_type(mime_type: str) -> str:
    """
    Gets the GtkSource.LanguageManager language id for a given mime type.
    Falls back to text if not found.
    """
    return language_map[content_type_map_reverse.get(mime_type) or 'text']


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
    def __init__(self, main_window):
        self.main_window = main_window
        self.active_request: Optional[RequestModel] = None
        self.last_response: Optional[requests.Response] = None

        builder = Gtk.Builder().new_from_file('ui/RequestEditor.glade')
        self.outer_box: Gtk.Box = builder.get_object('outerBox')

        self.request_method_combo: Gtk.ComboBox = builder.get_object('requestMethodCombo')
        self.request_method_combo_store: Gtk.ListStore = builder.get_object('requestMethodComboStore')

        self.request_name_entry: Gtk.Entry = builder.get_object('requestNameEntry')
        self.url_entry: Gtk.Entry = builder.get_object('urlEntry')
        self.send_button: Gtk.Button = builder.get_object('sendButton')
        self.save_button: Gtk.Button = builder.get_object('saveButton')

        self.request_response_stack_switcher: Gtk.StackSwitcher = builder.get_object('requestResponseStackSwitcher')
        self.request_response_stack: Gtk.Stack = builder.get_object('requestResponseStack')

        self.request_notebook: Gtk.Notebook = builder.get_object('requestNotebook')
        self.lang_manager = GtkSource.LanguageManager()
        self.request_text: GtkSource.View = builder.get_object('requestText')
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

        self.response_notebook: Gtk.Notebook = builder.get_object('responseNotebook')
        self.response_text_overlay: Gtk.Overlay = builder.get_object('responseTextOverlay')
        self.response_text: GtkSource.View = builder.get_object('responseText')
        self.response_text_raw: Gtk.TextView = builder.get_object('rawResponseView')
        self.response_webview_scroll_window: Gtk.ScrolledWindow = builder.get_object('webViewScrollWindow')
        # TODO: Lazy load the web view
        self.response_webview: WebKit2.WebView = WebKit2.WebView()\
            .new_with_context(WebKit2.WebContext().new_ephemeral())
        self.response_webview_scroll_window.add(self.response_webview)

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
       
        self.response_filter_search_entry: Gtk.SearchEntry = builder.get_object('responseFilterSearch')
        self.response_filter_search_bar: Gtk.SearchBar = builder.get_object('responseSearchBar')

        # Connections

        self.request_name_entry.connect('activate', self._on_request_name_changed)
        self.send_button.connect('clicked', self.on_send_pressed)
        self.save_button.connect('clicked', self.on_save_pressed)
        self.response_text.connect('populate-popup', self._populate_response_text_context_menu)
        self.request_type_popover_tree_view.connect('row-activated', self._on_popover_row_activated)
        self.request_type_notebook.connect('switch-page', self._on_request_type_notebook_page_switched)
        self.response_filter_search_entry.connect('search-changed', self._on_response_filter_changed)

    def _on_response_filter_changed(self, entry: Gtk.SearchEntry):
        filter_text = entry.get_text()
        if filter_text == '':
            self._set_response_text()

        ct = get_content_type(self.last_response)
        try:
            if ct == 'application/json':
                path_expr = jsonpath_rw.parse(filter_text)
                j = self.last_response.json()
                match_text = json.dumps([match.value for match in path_expr.find(j)], indent=4) or 'No matches found'
                self.response_text.get_buffer().set_text(match_text)
            elif ct in {'text/xml', 'application/xml'}:
                root = etree.fromstring(self.last_response.text)
                matches = root.xpath(filter_text)
                matches_root = etree.Element('matches')
                for m in matches:
                    matches_root.append(m)

                matches_html = etree.tostring(matches_root, encoding='unicode', pretty_print=True)
                self.response_text.get_buffer().set_text(matches_html)
            elif ct == 'text/html':
                root = html.fromstring(self.last_response.text)
                matches = root.xpath(filter_text)
                matches_root = etree.Element('matches')
                for m in matches:
                    matches_root.append(m)

                matches_html = etree.tostring(matches_root, encoding='unicode', pretty_print=True)
                self.response_text.get_buffer().set_text(matches_html)
            else:
                log.warning('Got unexpected content type %s when filtering response.', ct)
        except Exception as e:
            log.debug('Failed to filter response json %s', e)

    def _set_response_text(self):
        response = self.last_response
        ct = parse_content_type(response.headers.get('content-type'))
        if ct == 'application/json':
            j = response.json()
            txt = json.dumps(j, indent=2)
        elif ct in {'text/xml', 'application/xml'}:
            root = etree.fromstring(response.text)
            txt = etree.tostring(root, encoding='unicode', pretty_print=True)
        elif ct == 'text/html':  # TODO: Add css path filters
            root = html.fromstring(response.text)
            txt = etree.tostring(root, encoding='unicode', pretty_print=True)
        elif not response.text:
            txt = 'Empty Response'
        else:
            txt = response.text

        self.response_text.get_buffer().set_text(txt)

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

        lang = self.lang_manager.get_language(language_map[type_id])
        self.request_text.get_buffer().set_language(lang)

        if type_id == 'text':
            self.request_header_table.delete_row_by_key('content-type')
        else:
            self.request_header_table.prepend_or_update_row_by_key(('Content-Type', content_type_map[type_id], ''))

        self.request_type_popover.hide()
        self.request_type_notebook.set_current_page(1)

    def _on_request_name_changed(self, entry: Gtk.Entry):
        self.active_request = self.get_request()
        self.main_window.request_list.update_request(self.active_request)

    def _populate_response_text_context_menu(self, view: Gtk.TextView, popup: Gtk.Widget):
        if type(popup) is not Gtk.Menu:
            return

        menu: Gtk.Menu = popup

        word_wrap_toggle: Gtk.MenuItem = Gtk.MenuItem().new_with_label('Toggle word wrap')
        word_wrap_toggle.connect('activate', self._word_wrap_toggle_clicked)
        menu.append(word_wrap_toggle)

        ct = get_content_type(self.last_response)
        if self.last_response and ct in {'application/json', 'text/html', 'text/xml', 'application/xml'}:
            show_filter_toggle: Gtk.MenuItem = Gtk.MenuItem().new_with_label('Show response filter')
            show_filter_toggle.connect('activate', self._show_filter_toggle_clicked)
            menu.append(show_filter_toggle)

        menu.show_all()

    # def _reset_response_text_filter(self):
    #     ct = get_content_type(self.last_response)
    #     if ct == 'application/json':
    #     elif ct == 'text/html':

    def _show_filter_toggle_clicked(self, btn):
        is_revealed = self.response_filter_search_bar.get_search_mode()
        self.response_filter_search_bar.set_search_mode(not is_revealed)

    def _word_wrap_toggle_clicked(self, btn):
        current = self.response_text.get_wrap_mode()
        new = Gtk.WrapMode.NONE if current != Gtk.WrapMode.NONE else Gtk.WrapMode.WORD
        self.response_text.set_wrap_mode(new)

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

    def _format_request_url(self) -> str:
        url = self.url_entry.get_text()
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url
        return url

    def on_send_pressed(self, btn):
        url = self._format_request_url()
        meth_idx = self.request_method_combo.get_active()
        meth = self.request_method_combo_store[meth_idx][0]

        self.set_response_spinner_active(True)
        self.request_response_stack.set_visible_child(self.response_text_overlay)

        params = [(k, v) for k, v, _ in self.param_table.get_values()]
        headers = dict([(k, v) for k, v, _ in self.request_header_table.get_values()])
        body = self.get_body()

        TPE.submit(self.do_request, meth, url, params, headers, body)
        log.info('Creating request to %s - %s', meth, url)

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

    def do_request(self, method: str, url: str, params: List[Tuple[str, str]], headers: Dict[str, str], data=None):
        try:
            if type(data) is str:
                data = data.encode('utf-8')

            res = requests.request(method, url, params=params, headers=headers, data=data)
            # TODO: Load all the data into custom object before sending it back to UI thread
            GLib.idle_add(self.handle_request_finished, res)
        except Exception as e:
            log.error('Error occurred while sending request %s', e)
            GLib.idle_add(self.handle_request_finished_exceptionally, e)

    def handle_request_finished(self, response: requests.Response):
        log.info('Got %s response from %s', response.status_code, self.url_entry.get_text())
        self.last_response = response
        try:
            self._set_response_text()
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

            lang = self.lang_manager.get_language(get_language_for_mime_type(parse_content_type(response.headers.get('content-type'))))
            buf = self.response_text.get_buffer()
            buf.set_language(lang)
            # buf.set_text(txt)
            self.update_webview(response)
            self.response_text_raw.get_buffer().set_text(response.text)
            self.response_notebook.set_current_page(1)  # Body page
        finally:
            self.set_response_spinner_active(False)

    def update_webview(self, response: requests.Response):
        """Loads the webview, or show error message if webkit unavailable."""
        ct = parse_content_type(response.headers.get('content-type'))
        if not (response.request.method == 'GET' and response.ok and ct == 'text/html'):
            # self.response_webview.try_close()
            return

        # TODO: Enable running of javascript
        self.response_webview.load_html(response.text)

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
