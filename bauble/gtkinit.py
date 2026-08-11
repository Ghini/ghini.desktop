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


import logging

logger = logging.getLogger(__name__)

# Known-noisy, harmless GTK/GLib messages we choose not to show on the
# console. GLib.log_set_handler has no effect once structured logging is
# in use (the case on modern GLib), so filtering must happen in a writer
# function registered via GLib.log_set_writer_func instead.
_KNOWN_NOISY_SUBSTRINGS = (
    # GtkEditable/int marshalling warning
    ("g_value_get_int", "G_VALUE_HOLDS_INT"),
    # combo/completion on a Gtk.ListStore(object) model: GTK's internal
    # entry-text handling chokes on the object column; harmless, the
    # actual entry text is always set explicitly by our own code.
    ("gtk_entry_set_text",),
)


def _gtk_log_writer(log_level, fields, user_data=None):
    if log_level & (
        GLib.LogLevelFlags.LEVEL_WARNING | GLib.LogLevelFlags.LEVEL_CRITICAL
    ):
        message = GLib.log_writer_format_fields(log_level, fields, False)
        if any(
            all(needle in message for needle in needles)
            for needles in _KNOWN_NOISY_SUBSTRINGS
        ):
            logger.debug(message)
            return GLib.LogWriterOutput.HANDLED
    return GLib.log_writer_default(log_level, fields, user_data)


GLib.log_set_writer_func(_gtk_log_writer)
