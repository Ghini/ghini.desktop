#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2018 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
# Copyright 2017 Ross Demuth
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
import logging
import os
import traceback
from gettext import gettext as _
from threading import Thread
from typing import Any

import bauble
import bauble.paths as bpaths
import bauble.pluginmgr as pluginmgr
import bauble.utils as butils
from bauble.editor import GenericEditorPresenter, GenericEditorView
from bauble.error import BaubleError
from bauble.gtkinit import GLib, Gtk
from bauble.plugins.garden.models import Accession, Contact, Location, Plant, Source
from bauble.plugins.plants import Family, Genus, Species, VernacularName
from bauble.plugins.tag import Tag
from bauble.prefs import prefs
from sqlalchemy import select, union

from .flat_export import FlatFileExportTool as FlatFileExportTool
from .utils import PS, SVG

logger: Any
config_list_pref: str
default_config_pref: str

#
# __init__.py
#
# Description : report plugin
#

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# name: formatter_kwargs
config_list_pref = "report.options"

# the default report generator to select on start
default_config_pref = "report.xsl"
formatter_settings_expanded_pref: str = "report.settings.expanded"


def safe_set_text(gtk_widget, text) -> None:
    """
    Sets the text of a Gtk widget replacing None with an empty string.

    :param label: Instance of a Gtk widget
    :param text: The text to set, which may be None
    """
    if text is None:
        text = ""
    gtk_widget.set_text(text)


def get_plant_query(obj, session):
    """ """
    # .order_by(None) is needed for the later union() to work properly
    q = session.execute(select(Plant)).scalars()
    if isinstance(obj, Family):
        return (
            q.join(Accession, Plant.accession)
            .join(Species, Accession.species)
            .join(Genus, Species.genus)
            .join(Family, Genus.family)
            .where(Family.id == obj.id)
        )

    elif isinstance(obj, Genus):
        return (
            q.join(Accession, Plant.accession)
            .join(Species, Accession.species)
            .join(Genus, Species.genus)
            .where(Genus.id == obj.id)
        )

    elif isinstance(obj, Species):
        return (
            q.join(Accession, Plant.accession)
            .join(Species, Accession.species)
            .where(Species.id == obj.id)
        )

    elif isinstance(obj, VernacularName):
        return (
            q.join(Accession, Plant.accession)
            .join(Species, Accession.species)
            .join(Species.vernacular_names)
            .where(VernacularName.id == obj.id)
        )

    elif isinstance(obj, Plant):
        return q.where(Plant.id == obj.id)

    elif isinstance(obj, Accession):
        return q.join(Accession, Plant.accession).where(Accession.id == obj.id)

    elif isinstance(obj, Location):
        return q.where(Plant.location_id == obj.id)

    elif isinstance(obj, Contact):
        return (
            q.join(Accession, Plant.accession)
            .join(Source, Accession.source)
            .join(Contact, Source.source_detail)
            .where(Contact.id == obj.id)
        )

    elif isinstance(obj, Tag):
        plants = get_pertinent_objects(Plant, obj.objects)
        from sqlalchemy import bindparam

        return q.where(Plant.id.in_(bindparam("plant_ids", expanding=True))).params(
            plant_ids=[p.id for p in plants]
        )

    else:
        raise BaubleError(_("Can't get plants from a %s") % type(obj).__name__)


def get_accession_query(obj, session):
    """ """
    q = session.execute(select(Accession)).scalars()
    if isinstance(obj, Family):
        return (
            q.join(Species, Accession.species)
            .join(Genus, Species.genus)
            .join(Family, Genus.family)
            .where(Family.id == obj.id)
        )

    elif isinstance(obj, Genus):
        return (
            q.join(Species, Accession.species)
            .join(Genus, Species.genus)
            .where(Genus.id == obj.id)
        )

    elif isinstance(obj, Species):
        return q.join(Species, Accession.species).where(Species.id == obj.id)

    elif isinstance(obj, VernacularName):
        return (
            q.join(Species, Accession.species)
            .join(Species.vernacular_names)
            .where(VernacularName.id == obj.id)
        )

    elif isinstance(obj, Plant):
        return q.join(Plant, Accession.plants).where(Plant.id == obj.id)

    elif isinstance(obj, Accession):
        return q.where(Accession.id == obj.id)

    elif isinstance(obj, Location):
        return q.join(Plant, Accession.plants).where(Plant.location_id == obj.id)

    elif isinstance(obj, Contact):
        return (
            q.join(Source, Accession.source)
            .join(Contact, Source.source_detail)
            .where(Contact.id == obj.id)
        )

    elif isinstance(obj, Tag):
        acc = get_pertinent_objects(Accession, obj.objects)
        from sqlalchemy import bindparam

        return q.where(
            Accession.id.in_(bindparam("accession_ids", expanding=True))
        ).params(accession_ids=[a.id for a in acc])
    else:
        raise BaubleError(_("Can't get accessions from a %s") % type(obj).__name__)


def get_species_query(obj, session):
    """ """
    q = session.execute(select(Species)).scalars()
    if isinstance(obj, Family):
        return (
            q.join(Genus, Species.genus)
            .join(Family, Genus.family)
            .where(Family.id == obj.id)
        )

    elif isinstance(obj, Genus):
        return q.join(Genus, Species.genus).where(Genus.id == obj.id)

    elif isinstance(obj, Species):
        return q.where(Species.id == obj.id)

    elif isinstance(obj, VernacularName):
        return q.join(Species.vernacular_names).where(VernacularName.id == obj.id)

    elif isinstance(obj, Plant):
        return q.join(Accession.plants).where(Plant.id == obj.id)

    elif isinstance(obj, Accession):
        return q.where(Accession.id == obj.id)

    elif isinstance(obj, Location):
        return q.join(Accession.plants).where(Plant.location_id == obj.id)

    elif isinstance(obj, Contact):
        return (
            q.join(Accession.source)
            .join(Source.source_detail)
            .where(Contact.id == obj.id)
        )

    elif isinstance(obj, Tag):
        acc = get_pertinent_objects(Species, obj.objects)
        from sqlalchemy import bindparam

        return q.where(Species.id.in_(bindparam("species_ids", expanding=True))).params(
            species_ids=[a.id for a in acc]
        )

    else:
        raise BaubleError(_("Can't get species from a %s") % type(obj).__name__)


def get_location_query(obj, session):
    """ """
    stmt = select(Location)

    if isinstance(obj, Location):
        stmt = stmt.where(Location.id == obj.id)

    elif isinstance(obj, Plant):
        stmt = stmt.join(Plant.accession).where(Plant.id == obj.id)

    elif isinstance(obj, Accession):
        stmt = stmt.join(Plant.accession).where(Accession.id == obj.id)

    elif isinstance(obj, Family):
        stmt = (
            stmt.join(Plant.accession)
            .join(Accession.species)
            .join(Species.genus)
            .join(Genus.family)
            .where(Family.id == obj.id)
        )

    elif isinstance(obj, Genus):
        stmt = (
            stmt.join(Plant.accession)
            .join(Accession.species)
            .join(Species.genus)
            .where(Genus.id == obj.id)
        )

    elif isinstance(obj, Species):
        stmt = (
            stmt.join(Plant.accession)
            .join(Accession.species)
            .where(Species.id == obj.id)
        )

    elif isinstance(obj, VernacularName):
        stmt = (
            stmt.join(Plant.accession)
            .join(Accession.species)
            .join(Species.vernacular_names)
            .where(VernacularName.id == obj.id)
        )

    elif isinstance(obj, Contact):
        stmt = (
            stmt.join(Plant.accession)
            .join(Accession.source)
            .join(Source.source_detail)
            .where(Contact.id == obj.id)
        )

    elif isinstance(obj, Tag):
        locs = get_pertinent_objects(Location, obj.objects)
        from sqlalchemy import bindparam

        stmt = stmt.where(
            Location.id.in_(bindparam("location_ids", expanding=True))
        ).params(location_ids=[l.id for l in locs])

    else:
        raise BaubleError(_("Can't get Location from a %s") % type(obj).__name__)

    # Now execute and scalars at the end
    return session.execute(stmt).scalars()


def get_pertinent_objects(cls, objs):
    """return a query containing all `csl` objects reachable from `objs`

    :param cls:
    :param objs:
    """
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    from sqlalchemy.orm import object_session

    session = object_session(objs[0])

    get_query_func = {
        Plant: get_plant_query,
        Accession: get_accession_query,
        Species: get_species_query,
        Location: get_location_query,
    }[cls]

    queries = [get_query_func(o, session) for o in objs]
    unions = union(*[q.statement for q in queries])
    return session.execute(select(cls).from_statement(unions)).scalars()


class SettingsBox:
    """
    The interface to use for the settings box. Formatters should
    implement this interface and return it from the formatter's get_settings
    method.
    """

    vbox: Any

    def __init__(self) -> None:
        # Create an instance of Gtk.VBox instead of subclassing it
        self.vbox = Gtk.VBox()

    def get_settings(self) -> None:
        """
        Should be implemented by subclasses or other classes to retrieve
        the settings.
        """
        raise NotImplementedError

    def update(self, settings) -> None:
        """
        Should be implemented by subclasses or other classes to update
        the settings with the given data.
        """
        raise NotImplementedError

    def get_vbox(self):
        """
        Returns the Gtk.VBox instance managed by this class.
        """
        return self.vbox


class FormatterPlugin(pluginmgr.Plugin):
    """
    an interface class that a plugin should implement if it wants to generate
    reports with the ReportToolPlugin

    NOTE: the title class attribute must be a unique string
    """

    title: str = ""

    @classmethod
    def init(cls) -> None:
        """inform report presenter that this plugin is available

        (extend in derived classes)
        """
        cls.install()  # plugins still not versioned...
        ReportToolDialogPresenter.formatter_class_map[cls.title] = cls

    @staticmethod
    def format(objs, **kwargs) -> None:
        """
        called when the use clicks on OK, this is the worker
        """
        raise NotImplementedError

    @classmethod
    def get_template(cls, name):
        """return Template object corresponding to name within Plugin

        In principle, a Template object is what is going to perform the
        rendering, unless the Plugin overrides the behaviour.

        The contract with a minimum Template object is that its .filename
        field points to the original file name.

        """
        result = type("Template", (object,), {"filename": ""})()
        for path in [
            os.path.join(bpaths.user_dir(), "templates", name),
            os.path.join(bpaths.lib_dir(), "plugins", "report", "templates", name),
        ]:
            if os.path.exists(path):
                result.filename = path
                break
        return result

    @classmethod
    def can_handle(cls, name):
        """tell whether plugin can handle template"""
        try:
            if name.endswith(cls.extension):
                return cls.get_iteration_domain(name) != ""
            else:
                return False
        except Exception as e:
            logger.debug(
                f"{cls.title} can't handle template {name} - {type(e).__name__}({e})"
            )
            return False

    @classmethod
    def get_options(cls, name):
        """return template options list

        an element in the options list is a 4-tuple of strings, describing a
        field: (name, type, default, tooltip)

        """
        try:
            template = cls.get_template(name)
            filename = template.filename
            with open(filename) as f:
                option_lines = [
                    m
                    for m in [
                        cls.option_pattern.match(i.strip()) for i in f.readlines()
                    ]
                    if m is not None
                ]
        except:
            option_lines = []

        return [i.groups() for i in option_lines]

    @classmethod
    def get_iteration_domain(cls, name):
        """return template iteration domain

        a template that does not declare its iteration domain is not
        considered valid.

        """
        try:
            template = cls.get_template(name)
            filename = template.filename
            with open(filename) as f:
                domains = [
                    m.group(1)
                    for m in [
                        cls.domain_pattern.match(line.strip()) for line in f.readlines()
                    ]
                    if m is not None
                ]
                try:
                    domain = domains[0]
                except IndexError:
                    logger.debug(
                        f"template {template}({filename}) contains no {cls.title} DOMAIN declaration"
                    )
                    domain = ""
        except Exception as e:
            logger.debug(f"template {name} can't be read - {type(e).__name__}({e})")
            domain = ""

        return domain


class TemplateFormatterPlugin(FormatterPlugin):
    """intermediate base for template-based textual formatters.

    this is an abstract base class, used by Mako and Jinja2 formatter
    plugins.  you must override the `get_template` method, and define the
    four fields `title`, `extension`, `domain_pattern` and `option_pattern`.

    """

    @classmethod
    def install(cls, import_defaults: bool = True) -> None:
        "create templates dir on plugin installation"
        logger.debug(f"installing {cls.title} plugin")
        container_dir = os.path.join(bpaths.appdata_dir(), "templates")
        if not os.path.exists(container_dir):
            os.mkdir(container_dir)

    @classmethod
    def get_template(cls, filename) -> None:
        raise NotImplementedError

    @classmethod
    def format(cls, objs, **kwargs):
        template_name = kwargs["template"]
        kwargs.get("private", True)
        template = cls.get_template(template_name)

        from bauble import db

        session = db.Session()
        values = list(map(session.merge, objs))
        report = template.render(values=values, options=kwargs)
        session.close()
        # Template name is guaranteed in the form
        # ›<name>.<dotless-extension><cls.extension>‹.  Get the dotless
        # extension from the template file name, produce output with that
        # extension.
        head, ext = os.path.splitext(template_name[: -len(cls.extension)])
        import tempfile

        fd, filename = tempfile.mkstemp(suffix=ext)
        if isinstance(report, str):
            report = report.encode("utf8")
        os.write(fd, report)
        os.close(fd)
        try:
            butils.desktop.open(f"file://{filename}")
        except OSError:
            butils.message_dialog(
                _(
                    "Could not open the report with the "
                    "default program. You can open the "
                    "file manually at %s"
                )
                % filename
            )
        return report


class ReportToolDialogPresenter(GenericEditorPresenter):
    """presenter, and at same time model.

    Let user set parameters for report production, return them to invoking
    function, and die.

    """

    # to be populated by template plugins
    formatter_class_map: Any
    hard_coded_options: Any
    options: Any
    defaults: Any
    selection: Any
    session: Any
    work_thread: Any
    running: bool
    formatter_class_map = {}  # title->class

    def __init__(self, view) -> None:
        super().__init__(model=self, view=view, refresh_view=False)
        self.start_thread(Thread(target=self.populate_names_combo))

        self.view.widget_set_sensitive("ok_button", False)
        self.view.widget_set_sensitive("names_combo", False)

        # set the names combo to the default. this activates
        # on_names_combo_changes, which does the rest of the work
        self.view.widgets.names_combo
        default = prefs[default_config_pref]
        self.view.widget_set_value("names_combo", default)
        # hard_coded_options are part of the glade interface, we do not
        # remove them when selecting a different template.
        self.hard_coded_options = set(self.view.widgets.options_box.get_children())

    def set_prefs_for(self, name, settings) -> None:
        """
        This will overwrite any other report settings with name
        """
        template_options = prefs[config_list_pref] or {}
        template_options[name] = settings
        prefs[config_list_pref] = template_options

    def thaw_templates(self, *args) -> None:
        template_options = prefs[config_list_pref] or {}
        thawn = 0
        for key in template_options:
            try:
                del template_options[key]["__is_frozen__"]
                thawn += 1
            except:
                pass
        prefs[config_list_pref] = template_options
        self.start_thread(Thread(target=self.populate_names_combo))
        logger.debug(f"thawn {thawn} templates")

    def on_new_button_clicked(self, *args) -> None:
        filename = os.path.join(bpaths.lib_dir(), "plugins", "report", "report.glade")
        view = GenericEditorView(filename, root_widget_name="choose_dialog")
        GenericEditorPresenter(model=self, view=view)
        signaller = view.widgets.choose_thaw
        handler_id = signaller.connect("clicked", self.thaw_templates)

        names = {i[0] + i[3] for i in self.view.widgets.names_ls}
        while True:
            if view.get_window().run() != Gtk.ResponseType.OK:
                break
            template = view.widgets.choose_browse.get_filename()
            name = os.path.basename(template)
            if template is None:
                # ignore action on emtpy choice
                continue
            elif name in names:
                if (
                    butils.yes_no_dialog(
                        _(
                            "template name ›%s‹ is already in use.\ndo you mean to overwrite it?"
                        )
                        % name
                    )
                    is False
                ):
                    continue
            for plugin in list(self.formatter_class_map.values()):
                if plugin.can_handle(template):
                    break
            else:
                butils.message_dialog(
                    _("Not a template, or no valid formatter installed.")
                )
                continue

            self.set_prefs_for(name, {})
            # copy template to user data as name
            src = template
            dst = os.path.join(bpaths.user_dir(), "templates", name)
            import shutil

            shutil.copy(src, dst)
            # reflect changes in view
            self.add_name_to_combo_and_select_it(
                name, plugin, is_package_template=False
            )
            break
        signaller.disconnect(handler_id)
        view.cleanup()

    def on_remove_button_clicked(self, *args) -> None:
        """remove user-template, or mark package-template as hidden"""
        # remove the file if it's a user template
        index = self.view.widgets.names_combo.get_active()
        name, title, is_package, extension = self.view.widgets.names_ls[index]
        if not is_package:
            plugin = self.formatter_class_map[title]
            fullpath = plugin.get_template(name + extension).filename
            try:
                os.unlink(fullpath)
            except Exception as e:
                logger.debug(f"{type(e).__name__}({e})")

        # also mark any corresponding package template as hidden
        self.options["__is_frozen__"] = True
        self.save_formatter_settings()

        # then remove entry and set new position.  new position is next
        # item, unless we deleted the last, then it is the previous, unless
        # list became empty then it is cleared.
        active_iter = self.view.widgets.names_combo.get_active_iter()
        previous_iter = self.view.widgets.names_ls.iter_previous(active_iter)
        if self.view.widgets.names_ls.remove(active_iter):
            # normal case
            self.view.widgets.names_combo.set_active_iter(active_iter)
        else:
            # we deleted the last, so we move back
            self.view.widgets.names_combo.set_active_iter(previous_iter)

    def on_names_combo_changed(self, combo, *args) -> None:
        self.options = {}  # reset options before idle action
        index = self.view.widgets.names_combo.get_active()
        if index != -1:
            row = self.view.widgets.names_ls[index]
            name = row[0] + row[3]
            prefs[default_config_pref] = name  # set the default to the new name
        GLib.idle_add(self._names_combo_changed_idle, combo)

    def _names_combo_changed_idle(self, combo) -> None:
        index = self.view.widgets.names_combo.get_active()
        self.view.widget_set_sensitive("details_box", (index != -1))
        if index != -1:
            row = self.view.widgets.names_ls[index]
            name = row[0] + row[3]
        else:
            row = None
            name = ""

        settings = prefs[config_list_pref].get(name, {})

        # Reset fields and disable OK button
        self.view.widget_set_sensitive("ok_button", False)
        self.view.widget_set_value("basename_entry", "")
        self.view.widget_set_value("formatter_entry", "")
        self.view.widget_set_value("domain_entry", "")

        try:
            title = row[1]
            is_package_template = row[2]
            plugin = self.formatter_class_map[title]
            domain = plugin.get_iteration_domain(name)
            if domain == "":
                raise IndexError(name)
            if domain == "raw":
                search_result = bauble.gui.get_results_model()
                top_left_content = search_result[0][0]
                domain = f"({top_left_content.__class__.__name__.lower()})"

            self.view.widget_set_value("basename_entry", row[0])
            self.view.widget_set_value("formatter_entry", title)
            self.view.widget_set_value("domain_entry", domain)
            self.view.widget_set_sensitive("ok_button", True)
            self.view.widget_set_value("is_package_template", is_package_template)
        except Exception as e:
            logger.debug(f"Template {name} raised {type(e).__name__}({e}).")
            return

        self.set_prefs_for(name, settings)

        self.defaults = []
        options_box = self.view.widgets.options_box

        # Empty the options box (except hardcoded options)
        for child in options_box.get_children():
            if child in self.hard_coded_options:
                continue
            options_box.remove(child)

        # Retrieve template options
        option_fields = plugin.get_options(name)

        # Populate the options box
        for fname, ftype, fdefault, ftooltip in option_fields:
            row = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL, spacing=5
            )  # Replaces Gtk.HBox

            label = Gtk.Label(label=f"{fname.replace('_', ' ')}:")
            label.set_xalign(0)  # Instead of set_alignment(0, 0.5)
            label.set_yalign(0.5)

            ftype = ftype.lower()
            if ftype == "bool":
                fdefault = fdefault.lower() not in ["false", "0"]
                self.options.setdefault(fname, fdefault)
                entry = Gtk.CheckButton()
                entry.set_margin_start(4)  # Instead of set_margin_left(4)
                entry.set_active(self.options[fname])
                entry.connect("toggled", self.set_bool_option, fname)
            else:
                self.options.setdefault(fname, fdefault)
                entry = Gtk.Entry()
                safe_set_text(entry, self.options[fname])
                entry.connect("changed", self.set_option, fname)

            entry.set_tooltip_text(ftooltip)

            # Add entry to the row
            row.pack_start(label, False, False, 0)
            row.pack_start(entry, True, True, 0)

            # Store default values
            self.defaults.append((entry, fdefault))

            # Add to options box
            options_box.pack_start(row, False, False, 0)

        # Reset Button
        if self.defaults:
            reset_button = Gtk.Button(label=_("Reset to defaults"))
            reset_button.connect("clicked", self.reset_options)
            options_box.pack_start(reset_button, False, False, 0)

        options_box.show_all()

    def reset_options(self, widget) -> None:
        for entry, value in self.defaults:
            if isinstance(value, bool):
                entry.set_active(value)
            else:
                safe_set_text(entry, value)

    def set_option(self, widget, fname) -> None:
        self.options[fname] = widget.get_text()

    def set_bool_option(self, widget, fname) -> None:
        self.options[fname] = widget.get_active()

    def add_name_to_combo_and_select_it(
        self, name, plugin, is_package_template
    ) -> None:
        """the names tells it all

        scan through the names_ls, first compare with column:1, which holds
        the plugin.title, then compare with column:0, holding the template
        name, and they are both in alphabetical order.

        then insert the line relative to the new template.

        """

        new_row = (
            name[: -len(plugin.extension)],
            plugin.title,
            is_package_template,
            plugin.extension,
        )

        names_ls = self.view.widgets.names_ls
        item = names_ls.get_iter_first()
        for row in names_ls:
            if row[1] >= plugin.title and row[0] >= name:
                break
            item = names_ls.iter_next(item)
        if row[1] == plugin.title and row[0] == name:
            names_ls.set(item, [2], [False])
        elif item:
            item = names_ls.insert_before(item, new_row)
        else:
            item = names_ls.append(new_row)
        GLib.idle_add(butils.none, self.view.widgets.names_combo.set_active_iter, item)

    def populate_names_combo(self) -> None:
        """populate names_ls from package- and user-templates

        please note: prefs[config_list_pref] are just user defined settings.
        if a template can be found, it is considered active and should be
        shown in the combo.

        """
        options = prefs[config_list_pref]
        names = set()
        paths = [
            os.path.join(bpaths.user_dir(), "templates"),
            os.path.join(bpaths.lib_dir(), "plugins", "report", "templates"),
        ]
        # list of files which might be templates, and sorted by basename,
        # placing first user templates.
        basenames_fullnames = sorted(
            [
                (b, i, os.path.join(p, b))
                for (i, p) in enumerate(paths)
                for b in os.listdir(p)
            ]
        )
        self.view.widgets.names_ls.clear()
        for title in sorted(self.formatter_class_map):  # sort templates by plugin
            plugin = self.formatter_class_map[title]
            logger.debug(f"scanning {title} templates for {plugin}")
            for candidate, index, _path in basenames_fullnames:  # then by name
                name = candidate[: -len(plugin.extension)]
                if options.get(name, {}).get("__is_frozen__"):
                    continue
                if candidate in names:
                    # user template overrides homonymous package template
                    continue
                if plugin.can_handle(candidate):
                    logger.debug(
                        "{} accepts {}-template {}".format(
                            title,
                            index == 1 and "package" or "user",
                            candidate,
                        )
                    )
                    self.view.widgets.names_ls.append(
                        (name, title, index == 1, plugin.extension)
                    )
                    names.add(candidate)
                else:
                    logger.debug(f"{title} refuses {candidate}")
        GLib.idle_add(butils.none, self.view.widget_set_sensitive, "names_combo", True)

    def save_formatter_settings(self) -> None:
        template_options = prefs[config_list_pref]
        name = self.view.widget_get_value("names_combo")
        template_options[name] = self.options
        prefs[config_list_pref] = template_options

    def selection_to_domain(self, domain):
        """convert the selection to the corresponding domain

        if domain is one of species, accession, plant, location, then
        retrieve all objects in the domain that are associated to the
        selected objects.

        if domain looks like `(domain)`, then it is an implicit domain,
        i.e.: it was inferred from the selection itself, so the selection
        itself is what we need.

        if the domain is `raw`, also that tells us to return the raw
        selection (the template will handle it).

        """
        try:
            cls = {
                "plant": Plant,
                "accession": Accession,
                "species": Species,
                "location": Location,
            }[domain]
            return sorted(
                get_pertinent_objects(cls, self.selection),
                key=butils.natsort_key,
            )
        except KeyError:
            return self.selection

    def start(self) -> None:
        """collect user choices, invokes formatter, repeat."""
        results_model = bauble.gui.get_results_model()  # guaranteed not empty
        self.selection = [row[0] for row in results_model]  # only top level selected
        from sqlalchemy.orm import object_session

        self.session = object_session(self.selection[0])  # reuse the same session

        formatter = None
        settings = None
        while True:
            response = self.view.start()
            if response != Gtk.ResponseType.OK:
                break

            index = self.view.widgets.names_combo.get_active()
            row = self.view.widgets.names_ls[index]
            name = row[0] + row[3]
            prefs[default_config_pref] = name
            self.save_formatter_settings()
            settings = prefs[config_list_pref].get(name, {})
            settings["template"] = name
            domain = self.view.widget_get_value("domain_entry")
            title = self.view.widget_get_value("formatter_entry")
            formatter = self.formatter_class_map[title]
            todo = self.selection_to_domain(domain)
            if todo:
                self.work_thread = Thread(
                    target=self.run_thread, args=[formatter, todo, settings]
                )
                self.running = True
                GLib.timeout_add(200, self.update_progress)
                self.view.widgets.main_grid.set_sensitive(False)
                self.view.widget_set_sensitive("ok_button", False)
                self.view.widget_set_sensitive("cancel_button", False)
                self.work_thread.start()
            else:
                translated_name = {
                    "plant": _("plants/clones"),
                    "accession": _("accessions"),
                    "species": _("species"),
                    "location": _("locations"),
                }[domain]
                butils.message_dialog(
                    _(
                        "There are no %s in the search results.\n"
                        "Please try another search."
                    )
                    % translated_name
                )

        self.view.disconnect_all()

    def update_progress(self):
        if self.running:
            self.view.widgets.progressbar.pulse()
        return self.running

    def run_thread(self, formatter, todo, settings) -> None:
        from bauble import db

        session = db.Session()
        todo = [session.merge(i) for i in todo]
        try:
            formatter.format(todo, **settings)
        except Exception as e:
            butils.idle_message(
                f"formatting {len(todo)} objects of type {type((todo + [None])[0]).__name__}\n{type(e).__name__}({e})\n{traceback.format_exc()}",
                type=Gtk.MessageType.ERROR,
            )

        session.close()
        GLib.idle_add(self.stop_progress)

    def stop_progress(self) -> None:
        self.running = False
        self.work_thread.join()
        self.view.widgets.main_grid.set_sensitive(True)
        self.view.widget_set_sensitive("ok_button", True)
        self.view.widget_set_sensitive("cancel_button", True)
        self.view.widgets.progressbar.set_fraction(0)


class ReportTool(pluginmgr.Tool):
    category: Any = (_("Report"), "plugins/report/tool-report.png")
    label: Any = _("From Template")
    icon_name: str = "text-x-generic-template"

    @classmethod
    def start(cls) -> None:
        """ """
        # is anything selected?  if not, refuse even considering
        if not bauble.gui.get_results_model():
            return

        bauble.gui.set_busy(True)
        try:
            filename = os.path.join(
                bpaths.lib_dir(), "plugins", "report", "report.glade"
            )
            view = GenericEditorView(filename, root_widget_name="report_dialog")
            presenter = ReportToolDialogPresenter(view)
            presenter.start()
        except AssertionError as e:
            logger.debug(e)
            logger.debug(traceback.format_exc())
            parent = None
            if hasattr(cls, "view") and hasattr(cls.view, "dialog"):
                parent = cls.view.get_window()

            butils.message_details_dialog(
                f"AssertionError({e})",
                traceback.format_exc(),
                Gtk.MessageType.ERROR,
                parent=parent,
            )
        except Exception as e:
            logger.debug(traceback.format_exc())
            butils.message_details_dialog(
                _("Formatting Error\n\n" "%s(%s)") % (type(e).__name__, butils.to_unicode(e)),
                traceback.format_exc(),
                Gtk.MessageType.ERROR,
            )
        bauble.gui.set_busy(False)
        return


class ReportToolPlugin(pluginmgr.Plugin):
    """ """

    tools: Any = [
        ReportTool,
        FlatFileExportTool,
    ]


try:
    import lxml._elementpath  # put this here so py2exe picks it up
    import lxml.etree as etree
except ImportError:
    butils.message_dialog(
        "The <i>lxml</i> package is required for the " "Report plugin"
    )
else:

    def plugin():
        from bauble.plugins.report.jinja2 import Jinja2FormatterPlugin
        from bauble.plugins.report.mako import MakoFormatterPlugin
        from bauble.plugins.report.xsl import XSLFormatterPlugin

        return [
            ReportToolPlugin,
            XSLFormatterPlugin,
            MakoFormatterPlugin,
            Jinja2FormatterPlugin,
        ]
