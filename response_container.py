import json
import logging
from typing import Optional

import jsonpath_rw
import requests
from gi.repository import Gtk, GtkSource, WebKit2
from lxml import etree, html

from utils import get_content_type, timedelta_fmt, format_response_size, get_language_for_mime_type

log = logging.getLogger(__name__)


class ResponseContainer:
    def __init__(self, request_editor):
        self.last_response: Optional[requests.Response] = None

        builder = Gtk.Builder().new_from_file('ui/ResponseContainer.glade')
        self.response_text_overlay: Gtk.Overlay = builder.get_object('responseTextOverlay')

        self.lang_manager = GtkSource.LanguageManager()

        self.response_notebook: Gtk.Notebook = builder.get_object('responseNotebook')
        self.response_text_overlay: Gtk.Overlay = builder.get_object('responseTextOverlay')
        self.response_text: GtkSource.View = builder.get_object('responseText')
        self.response_text_raw: Gtk.TextView = builder.get_object('rawResponseView')
        self.response_webview_scroll_window: Gtk.ScrolledWindow = builder.get_object('webViewScrollWindow')
        # TODO: Lazy load the web view
        self.response_webview: WebKit2.WebView = WebKit2.WebView() \
            .new_with_context(WebKit2.WebContext().new_ephemeral())
        self.response_webview_scroll_window.add(self.response_webview)

        self.response_loading_spinner: Gtk.Spinner = builder.get_object('responseLoadingSpinner')
        self.response_headers_text: Gtk.TextView = builder.get_object('responseHeadersText')
        self.response_status_label: Gtk.Label = builder.get_object('responseStatusLabel')
        self.response_time_label: Gtk.Label = builder.get_object('responseTimeLabel')
        self.response_size_label: Gtk.Label = builder.get_object('responseSizeLabel')

        self.response_filter_search_entry: Gtk.SearchEntry = builder.get_object('responseFilterSearch')
        self.response_filter_search_bar: Gtk.SearchBar = builder.get_object('responseSearchBar')

        # Connections

        self.response_text.connect('populate-popup', self._populate_response_text_context_menu)
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
        ct = get_content_type(response)
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

    def _show_filter_toggle_clicked(self, btn):
        is_revealed = self.response_filter_search_bar.get_search_mode()
        self.response_filter_search_bar.set_search_mode(not is_revealed)

    def set_response_spinner_active(self, active: bool):
        if active:
            self.response_loading_spinner.start()
            self.response_text_overlay.reorder_overlay(self.response_loading_spinner, 1)
        else:
            self.response_loading_spinner.stop()
            self.response_text_overlay.reorder_overlay(self.response_loading_spinner, 0)

    def update_webview(self, response: requests.Response):
        """Loads the webview, or show error message if webkit unavailable."""
        ct = get_content_type(response)
        if not (response.request.method == 'GET' and response.ok and ct == 'text/html'):
            # self.response_webview.try_close()
            return

        # TODO: Enable running of javascript
        self.response_webview.load_html(response.text)

    def _word_wrap_toggle_clicked(self, btn):
        current = self.response_text.get_wrap_mode()
        new = Gtk.WrapMode.NONE if current != Gtk.WrapMode.NONE else Gtk.WrapMode.WORD
        self.response_text.set_wrap_mode(new)

    def handle_request_finished(self, response: requests.Response):
        log.info('Got %s response from %s', response.status_code, response.url)
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

            lang = self.lang_manager.get_language(get_language_for_mime_type(get_content_type(response)))
            buf = self.response_text.get_buffer()
            buf.set_language(lang)
            # buf.set_text(txt)
            self.update_webview(response)
            self.response_text_raw.get_buffer().set_text(response.text)
            self.response_notebook.set_current_page(1)  # Body page
        finally:
            self.set_response_spinner_active(False)

    def handle_request_finished_exceptionally(self, ex: Exception):
        self.set_response_spinner_active(False)
        self.response_text.get_buffer().set_text(f'Error occurred while performing request: {ex}')
        self.response_notebook.set_current_page(1)  # Body page
