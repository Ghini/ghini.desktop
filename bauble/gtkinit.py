# bauble/gtkinit.py
import sys
from gettext import gettext as _

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")
gi.require_version("Gtk", "3.0")
gi.require_version("Champlain", "0.12")
gi.require_version("GtkChamplain", "0.12")
gi.require_version("GtkClutter", "1.0")

__all__ = [
    "Champlain",
    "Clutter",
    "Gdk",
    "GdkPixbuf",
    "Gio",
    "GLib",
    "GObject",
    "Gtk",
    "GtkChamplain",
    "GtkClutter",
    "Pango",
]

try:
    from gi.repository import (  # Ensures compatibility
        Champlain,
        Clutter,
        Gdk,
        GdkPixbuf,
        Gio,
        GLib,
        GObject,
        Gtk,
        GtkChamplain,
        GtkClutter,
        Pango,
    )
except ImportError as e:
    print(_("** Error: could not import Gtk and/or GObject"))
    print(e)
    if sys.platform == "win32":
        print(_("Please make sure that GTK_ROOT\\bin is in your PATH."))
    sys.exit(1)

def _gtk_warning_filter(domain, level, message, user_data=None):
    # Drop only the noisy GtkEditable/int marshalling warning
    if ("g_value_get_int" in message and "G_VALUE_HOLDS_INT" in message):
        return
    # Otherwise, forward to the default handler
    GLib.log_default_handler(domain, level, message, user_data)

for domain in ("Gtk", "GObject", "GLib-GObject"):
    GLib.log_set_handler(
        domain,
        GLib.LogLevelFlags.LEVEL_WARNING | GLib.LogLevelFlags.LEVEL_CRITICAL,
        _gtk_warning_filter,
        None,
    )
