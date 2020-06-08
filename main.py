import logging

import gi
gi.require_version("Gtk", "3.0")
gi.require_version('GtkSource', '4')
gi.require_version('WebKit2', '4.0')  # TODO: Ensure we don't crash if webkit isn't available
from gi.repository import Gtk, GtkSource, Gdk

from widgets.main_window import MainWindow

logging.basicConfig(
    format='%(asctime)s - %(module)s - [%(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p',
    level=logging.INFO)

log = logging.getLogger(__name__)


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
