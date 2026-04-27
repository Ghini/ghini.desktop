# shared.py

import logging
from typing import Any, Optional

from bauble import prefs
from bauble.gtkinit import Gio, Gtk

# from bauble.gtkinit import Pango
from bauble.utils import set_widget_value

logger: Any = logging.getLogger(__name__)

import logging

logger = logging.getLogger(__name__)


class InfoExpander:
    """
    A generic expander widget with a vbox for structured layout.

    To extend this, implement the `update()` method.
    """

    # Preference for storing the expanded state
    expanded_pref: Any
    expander: Any
    vbox: Any
    widgets: Any
    expanded_pref = None

    def __init__(self, label, widgets: Optional[Any] = None) -> None:
        """
        :param label: The name of this info expander, displayed on the expander.
        :param widgets: A bauble.utils.BuilderWidgets instance.
        """
        self.expander = Gtk.Expander(label=label)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.vbox.set_border_width(5)
        self.expander.add(self.vbox)
        self.widgets = widgets or {}  # Ensure widgets is always a dictionary

        if not self.expanded_pref:
            self.expander.set_expanded(True)

        self.expander.connect("notify::expanded", self.on_expanded)

    def get_widget(self):
        """Return the main widget (Gtk.Expander) for integration in UI layouts."""
        return self.expander

    def on_expanded(self, expander, *args) -> None:
        """
        Save the expanded state in preferences, if specified.
        """
        if self.expanded_pref:
            prefs.prefs[self.expanded_pref] = expander.get_expanded()
            prefs.prefs.save()

    def set_labeled_value(self, prefix, value) -> None:
        """
        Toggle visibility of a labeled field and set its value.

        Labels and data widgets are identified using `prefix+'_label'`
        and `prefix+'_data'`.

        :param prefix: The identifier for the label and data widgets.
        :param value: The value to set. If empty, hides the widgets.
        """
        label_widget = self.widgets.get(f"{prefix}_label")
        data_widget = self.widgets.get(f"{prefix}_data")

        if data_widget and label_widget:
            if value:
                self.widget_set_value(f"{prefix}_data", value)
                label_widget.set_visible(True)
                data_widget.set_visible(True)
            else:
                label_widget.set_visible(False)
                data_widget.set_visible(False)
        else:
            logger.warning(f"Widgets for prefix '{prefix}' not found.")

    def widget_set_value(
        self, widget_name, value, markup: bool = False, default: Optional[Any] = None
    ) -> None:
        """
        A shorthand for L{bauble.utils.set_widget_value()}
        """
        if widget_name in self.widgets:
            set_widget_value(self.widgets[widget_name], value, markup, default)

    def update(self, value) -> None:
        """
        This method should be implemented by classes that extend InfoExpander.
        """
        raise NotImplementedError("InfoExpander.update(): not implemented")


class Action:
    """
    Represents an action with a callback and optional visibility toggles.

    Uses `Gio.SimpleAction`, as `Gtk.Action` is deprecated in GTK 4.
    """

    name: Any
    label: Any
    tooltip: Any
    stock_id: Any
    callback: Any
    app: Any
    action: Any

    def __init__(
        self,
        name,
        label,
        tooltip: Optional[Any] = None,
        stock_id: Optional[Any] = None,
        callback: Optional[Any] = None,
        app: Optional[Any] = None,
    ) -> None:
        """
        :param name: Unique action name (e.g., "open").
        :param label: The action label.
        :param tooltip: Tooltip text.
        :param stock_id: Icon name for the action.
        :param callback: Function to execute when activated.
        :param app: The `Gtk.Application` where the action will be registered.
        """
        self.name = name
        self.label = label
        self.tooltip = tooltip
        self.stock_id = stock_id  # Save stock_id for potential icon use
        self.callback = callback
        self.app = app

        # Create the action
        self.action = Gio.SimpleAction.new(name, None)
        if callback:
            self.action.connect("activate", self._on_activate)

        # Register the action with the application if provided
        if app:
            app.add_action(self.action)

    def _on_activate(self, action, param) -> None:
        """Call the provided callback function when activated."""
        if self.callback:
            self.callback()

    def set_enabled(self, enable) -> None:
        """Enable or disable the action."""
        self.action.set_enabled(enable)

    def get_enabled(self):
        """Check if the action is enabled."""
        return self.action.get_enabled()

    enabled: Any = property(get_enabled, set_enabled)

    def execute(self, *args) -> None:
        """Manually trigger the action execution."""
        self._on_activate(None, None)
