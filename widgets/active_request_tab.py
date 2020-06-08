from gi.repository import Gtk

from models import RequestTreeNode


@Gtk.Template.from_file('ui/ActiveRequestTab.glade')
class ActiveRequestTab(Gtk.Box):
    __gtype_name__ = 'ActiveRequestTab'

    request_name_label: Gtk.Label = Gtk.Template.Child()
    close_request_button: Gtk.Button = Gtk.Template.Child()

    def __init__(self, main_window, page: Gtk.Widget, request_node: RequestTreeNode):
        super(ActiveRequestTab, self).__init__()

        assert not request_node.is_folder()

        self.main_window = main_window
        self.page = page

        self.request_node = request_node
        self.request_name_label.set_text(request_node.request.name)

    @Gtk.Template.Callback('close_button_clicked')
    def _on_close_button_clicked(self, btn: Gtk.Button):
        print('Close button clicked', btn)
        self.main_window.close_tab(self)
