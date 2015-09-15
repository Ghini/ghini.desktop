# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.
#
# Description: the default view
#
import itertools
import os
import sys
import traceback
import cgi

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import gtk
import gobject
import pango

from bauble.i18n import _
from pyparsing import ParseException
from sqlalchemy.orm import object_session
import sqlalchemy.exc as saexc

import bauble
import bauble.db as db
from bauble.error import check, BaubleError
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
import bauble.prefs as prefs
import bauble.search as search
import bauble.utils as utils
import bauble.pictures_view as pictures_view

# use different formatting template for the result view depending on the
# platform
_mainstr_tmpl = '<b>%s</b>'
if sys.platform == 'win32':
    _substr_tmpl = '%s'
else:
    _substr_tmpl = '<small>%s</small>'


class Action(gtk.Action):

    """
    An Action allows a label, tooltip, callback and accelerator to be called
    when specific items are selected in the SearchView
    """
    # issue #30: multiselect and singleselect are really specific to the
    # SearchView and we could probably generalize this class a little bit
    # more...or we just assume this class is specific to the SearchView and
    # document it that way

    def __init__(self, name, label, tooltip=None, stock_id=None,
                 callback=None, accelerator=None,
                 multiselect=False, singleselect=True):
        """
        callback: the function to call when the the action is activated
        accelerator: accelerator to call this action
        multiselect: show menu when multiple items are selected
        singleselect: show menu when single items are selected

        The activate signal is not automatically connected to the
        callback method.
        """
        super(Action, self).__init__(name, label, tooltip, stock_id)
        self.callback = callback
        self.multiselect = multiselect
        self.singleselect = singleselect
        self.accelerator = accelerator

    def _set_enabled(self, enable):
        self.set_visible(enable)
        # if enable:
        #     self.connect_accelerator()
        # else:
        #     self.disconnect_accelerator()

    def _get_enabled(self):
        return self.get_visible()

    enabled = property(_get_enabled, _set_enabled)


class InfoExpander(gtk.Expander):
    """
    an abstract class that is really just a generic expander with a vbox
    to extend this you just have to implement the update() method
    """

    # preference for storing the expanded state
    expanded_pref = None

    def __init__(self, label, widgets=None):
        """
        :param label: the name of this info expander, this is displayed on the
        expander's expander

        :param widgets: a bauble.utils.BuilderWidgets instance
        """
        super(InfoExpander, self).__init__(label)
        self.vbox = gtk.VBox(False)
        self.vbox.set_border_width(5)
        self.add(self.vbox)
        self.widgets = widgets
        if not self.expanded_pref:
            self.set_expanded(True)
        self.connect("notify::expanded", self.on_expanded)

    def on_expanded(self, expander, *args):
        if self.expanded_pref:
            prefs.prefs[self.expanded_pref] = expander.get_expanded()
            prefs.prefs.save()

    def widget_set_value(self, widget_name, value, markup=False, default=None):
        '''
        a shorthand for L{bauble.utils.set_widget_value()}
        '''
        utils.set_widget_value(self.widgets[widget_name], value,
                               markup, default)

    def update(self, value):
        '''
        This method should be implemented by classes that extend InfoExpander
        '''
        raise NotImplementedError("InfoExpander.update(): not implemented")


class PropertiesExpander(InfoExpander):

    def __init__(self):
        super(PropertiesExpander, self).__init__(_('Properties'))
        table = gtk.Table(rows=4, columns=2)
        table.set_col_spacings(15)
        table.set_row_spacings(8)

        # database id
        id_label = gtk.Label("<b>"+_("ID:")+"</b>")
        id_label.set_use_markup(True)
        id_label.set_alignment(1, .5)
        self.id_data = gtk.Label('--')
        self.id_data.set_alignment(0, .5)
        table.attach(id_label, 0, 1, 0, 1)
        table.attach(self.id_data, 1, 2, 0, 1)

        # object type
        type_label = gtk.Label("<b>"+_("Type:")+"</b>")
        type_label.set_use_markup(True)
        type_label.set_alignment(1, .5)
        self.type_data = gtk.Label('--')
        self.type_data.set_alignment(0, .5)
        table.attach(type_label, 0, 1, 1, 2)
        table.attach(self.type_data, 1, 2, 1, 2)

        # date created
        created_label = gtk.Label("<b>"+_("Date created:")+"</b>")
        created_label.set_use_markup(True)
        created_label.set_alignment(1, .5)
        self.created_data = gtk.Label('--')
        self.created_data.set_alignment(0, .5)
        table.attach(created_label, 0, 1, 2, 3)
        table.attach(self.created_data, 1, 2, 2, 3)

        # date last updated
        updated_label = gtk.Label("<b>"+_("Last updated:")+"</b>")
        updated_label.set_use_markup(True)
        updated_label.set_alignment(1, .5)
        self.updated_data = gtk.Label('--')
        self.updated_data.set_alignment(0, .5)
        table.attach(updated_label, 0, 1, 3, 4)
        table.attach(self.updated_data, 1, 2, 3, 4)

        box = gtk.HBox()
        box.pack_start(table, expand=False, fill=False)
        self.vbox.pack_start(box, expand=False, fill=False)

    def update(self, row):
        """"
        Update the widget in the expander.
        """
        self.id_data.set_text(str(row.id))
        self.type_data.set_text(str(type(row).__name__))
        self.created_data.set_text(
            row._created
            and row._created.strftime('%Y-%m-%d %H:%m:%S')
            or '')
        self.updated_data.set_text(
            row._last_updated
            and row._last_updated.strftime('%Y-%m-%d %H:%m:%S')
            or '')


class InfoBoxPage(gtk.ScrolledWindow):
    """
    A :class:`gtk.ScrolledWindow` that contains
    :class:`bauble.view.InfoExpander` objects.
    """

    def __init__(self):
        super(InfoBoxPage, self).__init__()
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.vbox = gtk.VBox()
        self.vbox.set_spacing(10)
        viewport = gtk.Viewport()
        viewport.add(self.vbox)
        self.add(viewport)
        self.expanders = {}
        self.label = None

    def add_expander(self, expander):
        '''
        Add an expander to the list of exanders in this infobox

        :param expander: the bauble.view.InfoExpander to add to this infobox
        '''
        self.vbox.pack_start(expander, expand=False, fill=True, padding=5)
        self.expanders[expander.get_property("label")] = expander

        expander._sep = gtk.HSeparator()
        self.vbox.pack_start(expander._sep, False, False)

    def get_expander(self, label):
        """
        Returns an expander by the expander's label name

        :param label: the name of the expander to return
        """
        if label in self.expanders:
            return self.expanders[label]
        else:
            return None

    def remove_expander(self, label):
        """
        Remove expander from the infobox by the expander's label bel

        :param label: the name of th expander to remove

        Return the expander that was removed from the infobox.
        """
        if label in self.expanders:
            return self.vbox.remove(self.expanders[label])

    def update(self, row):
        """
        Updates the infobox with values from row

        :param row: the mapper instance to use to update this infobox,
          this is passed to each of the infoexpanders in turn
        """
        for expander in self.expanders.values():
            expander.update(row)


class InfoBox(gtk.Notebook):
    """
    Holds list of expanders with an optional tabbed layout.

    The default is to not use tabs. To create the InfoBox with tabs
    use InfoBox(tabbed=True).  When using tabs then you can either add
    expanders directly to the InfoBoxPage or using
    InfoBox.add_expander with the page_num argument.

    Also, it's not recommended to create a subclass of a subclass of
    InfoBox since if they both use bauble.utils.BuilderWidgets then
    the widgets will be parented to the infobox that is created first
    and the expanders of the second infobox will appear empty.
    """

    def __init__(self, tabbed=False):
        super(InfoBox, self).__init__()
        self.row = None
        self.set_property('show-border', False)
        if not tabbed:
            page = InfoBoxPage()
            self.insert_page(page, position=0)
            self.set_property('show-tabs', False)
        self.set_current_page(0)
        self.connect('switch-page', self.on_switch_page)

    # not sure why we pass have self and notebook in the arg list here
    # since they are the same
    def on_switch_page(self, notebook, dummy_page, page_num,  *args):
        """
        Called when a page is switched
        """
        if not self.row:
            return
        page = self.get_nth_page(page_num)
        page.update(self.row)

    def add_expander(self, expander, page_num=0):
        """
        Add an expander to a page.

        :param expander: The expander to add.
        :param page_num: The page number in the InfoBox to add the expander.
        """
        page = self.get_nth_page(page_num)
        page.add_expander(expander)

    def update(self, row):
        """
        Update the current page with row.
        """
        self.row = row
        page_num = self.get_current_page()
        self.get_nth_page(page_num).update(row)


class LinksExpander(InfoExpander):

    def __init__(self, notes=None):
        """
        :param notes: the name of the notes property on the row
        """
        super(LinksExpander, self).__init__(_("Links"))
        self.dynamic_box = gtk.VBox()
        self.vbox.pack_start(self.dynamic_box)
        self.notes = notes

    def update(self, row):
        import pango
        map(self.dynamic_box.remove, self.dynamic_box.get_children())
        if self.notes:
            notes = getattr(row, self.notes)
            for note in notes:
                for label, url in utils.get_urls(note.note):
                    if not label:
                        label = url
                    label = gtk.Label(label)
                    label.set_ellipsize(pango.ELLIPSIZE_END)
                    button = gtk.LinkButton(uri=url)
                    button.add(label)
                    button.set_alignment(0, -1)
                    self.dynamic_box.pack_start(
                        button, expand=False, fill=False)
            self.dynamic_box.show_all()


class SearchView(pluginmgr.View):
    """
    The SearchView is the main view for Bauble.  It manages the search
    results returned when search strings are entered into the main
    text entry.
    """

    class ViewMeta(dict):
        """
        This class shouldn't need to be instantiated directly.  Access
        the meta for the SearchView with the
        :class:`bauble.view.SearchView`'s view_meta property.
        """
        class Meta(object):
            def __init__(self):
                self.children = None
                self.infobox = None
                self.markup_func = None
                self.actions = []

            def set(self, children=None, infobox=None, context_menu=None,
                    markup_func=None):
                '''
                :param children: where to find the children for this type,
                    can be a callable of the form C{children(row)}

                :param infobox: the infobox for this type

                :param context_menu: a dict describing the context menu used
                when the user right clicks on this type

                :param markup_func: the function to call to markup
                search results of this type, if markup_func is None
                the instances __str__() function is called...the
                strings returned by this function should escape any
                non markup characters
                '''
                self.children = children
                self.infobox = infobox
                self.markup_func = markup_func
                self.context_menu = context_menu
                self.actions = []
                if self.context_menu:
                    self.actions = filter(lambda x: isinstance(x, Action),
                                          self.context_menu)

            def get_children(self, obj):
                '''
                :param obj: get the children from obj according to
                self.children,

                Returns a list or list-like object.
                '''
                if self.children is None:
                    return []
                if callable(self.children):
                    return self.children(obj)
                return getattr(obj, self.children)

        def __getitem__(self, item):
            if item not in self:  # create on demand
                self[item] = self.Meta()
            return self.get(item)

    view_meta = ViewMeta()

    def __init__(self):
        '''
        the constructor
        '''
        super(SearchView, self).__init__()
        filename = os.path.join(paths.lib_dir(), 'bauble.glade')
        self.widgets = utils.load_widgets(filename)

        self.create_gui()

        import pictures_view
        pictures_view.floating_window = pictures_view.PicturesView(
            parent=self.widgets.search_h2pane)

        # we only need this for the timeout version of populate_results
        self.populate_callback_id = None

        # the context menu cache holds the context menus by type in the results
        # view so that we don't have to rebuild them every time
        self.context_menu_cache = {}
        self.infobox_cache = {}
        self.infobox = None

        # keep all the search results in the same session, this should
        # be cleared when we do a new search
        self.session = db.Session()

    def update_notes(self):
        """
        Update the notes treeview with the notes from the currently
        selected item.
        """
        values = self.get_selected_values()
        if len(values) != 1:
            self._notes_expanded = self.widgets.notes_expander.props.expanded
            self.widgets.notes_expander.hide()
            return

        row = values[0]
        if hasattr(row, 'notes') and isinstance(row.notes, list):
            self.widgets.notes_expander.show()
        else:
            self.widgets.notes_expander.hide()
            return

        if len(row.notes) > 0:
            self.widgets.notes_expander.props.sensitive = True
            self.widgets.notes_expander.props.expanded = self._notes_expanded
            model = gtk.ListStore(object)
            for note in row.notes:
                model.append([note])
            self.widgets.notes_treeview.set_model(model)
        else:
            self.widgets.notes_expander.props.expanded = False
            self.widgets.notes_expander.props.sensitive = False

    def update_infobox(self):
        '''
        Sets the infobox according to the currently selected row
        or remove the infobox is nothing is selected
        '''

        def set_infobox_from_row(row):
            '''implement the logic for update_infobox'''

            logger.debug('set_infobox_from_row: %s --  %s' % (row, repr(row)))
            # remove the current infobox if there is one and it is not needed
            if row is None:
                if self.infobox is not None and \
                        self.infobox.parent == self.pane:
                    self.pane.remove(self.infobox)
                return

            new_infobox = None
            selected_type = type(row)

            # if we have already created an infobox of this type:
            if selected_type in self.infobox_cache.keys():
                new_infobox = self.infobox_cache[selected_type]
            # if selected_type defines an infobox class:
            elif selected_type in self.view_meta and \
                    self.view_meta[selected_type].infobox is not None:
                logger.debug('%s defines infobox class %s'
                             % (selected_type,
                                self.view_meta[selected_type].infobox))
                # it might be in cache under different name
                for ib in self.infobox_cache.values():
                    if isinstance(ib, self.view_meta[selected_type].infobox):
                        logger.debug('found same infobox under different name')
                        new_infobox = ib
                # otherwise create one and put in the infobox_cache
                if not new_infobox:
                    logger.debug('not found infobox, we make a new one')
                    new_infobox = self.view_meta[selected_type].infobox()
                self.infobox_cache[selected_type] = new_infobox
            logger.debug('created or retrieved infobox %s %s'
                         % (type(new_infobox), new_infobox))

            # remove any old infoboxes connected to the pane
            if self.infobox is not None and \
                    type(self.infobox) != type(new_infobox):
                if self.infobox.parent == self.pane:
                    self.pane.remove(self.infobox)

            # update the infobox and put it in the pane
            self.infobox = new_infobox
            if self.infobox is not None:
                self.pane.pack2(self.infobox, resize=False, shrink=True)
                self.pane.show_all()
                self.infobox.update(row)

        # start of update_infobox
        logger.debug('update_infobox')
        values = self.get_selected_values()
        if not values:
            set_infobox_from_row(None)
            return

        try:
            set_infobox_from_row(values[0])
        except Exception, e:
            # if an error occurrs, log it and empty infobox.
            logger.debug('SearchView.update_infobox: %s' % e)
            logger.debug(traceback.format_exc())
            logger.debug(values)
            set_infobox_from_row(None)

    def get_selected_values(self):
        '''
        Return the values in all the selected rows.
        '''
        model, rows = self.results_view.get_selection().get_selected_rows()
        if model is None:
            return None
        return [model[row][0] for row in rows]

    def on_cursor_changed(self, view):
        '''
        Update the infobox and switch the accelerators depending on the
        type of the row that the cursor points to.
        '''
        self.update_infobox()
        self.update_notes()
        pictures_view.floating_window.set_selection(self.get_selected_values())

        for accel, cb in self.installed_accels:
            # disconnect previously installed accelerators by the key
            # and modifier, accel_group.disconnect_by_func won't work
            # here since we install a closure as the actual callback
            # in instead of the original action.callback
            r = self.accel_group.disconnect_key(accel[0], accel[1])
            if not r:
                logger.warning('callback not removed: %s' % cb)
        self.installed_accels = []

        selected = self.get_selected_values()
        if not selected:
            return
        selected_type = type(selected[0])

        for action in self.view_meta[selected_type].actions:
            enabled = (len(selected) > 1 and action.multiselect) or \
                (len(selected) <= 1 and action.singleselect)
            if not enabled:
                continue
            # if enabled then connect the accelerator
            keyval, mod = gtk.accelerator_parse(action.accelerator)
            if (keyval, mod) != (0, 0):
                def cb(func):
                    def _impl(*args):
                        # getting the selected here allows the
                        # callback to be called on all the selected
                        # values and not just the value where the
                        # cursor is
                        sel = self.get_selected_values()
                        if func(sel):
                            self.reset_view()
                    return _impl
                self.accel_group.connect_group(keyval, mod,
                                               gtk.ACCEL_VISIBLE,
                                               cb(action.callback))
                self.installed_accels.append(((keyval, mod), action.callback))
            else:
                logger.warning(
                    'Could not parse accelerator: %s' % (action.accelerator))

    nresults_statusbar_context = 'searchview.nresults'

    def search(self, text):
        """
        search the database using text
        """
        # set the text in the entry even though in most cases the entry already
        # has the same text in it, this is in case this method was called from
        # outside the class so the entry and search results match
        logger.debug('SearchView.search(%s)' % text)
        error_msg = None
        error_details_msg = None
        self.session.close()
        # create a new session for each search...maybe we shouldn't
        # even have session as a class attribute
        self.session = db.Session()
        bold = '<b>%s</b>'
        results = []
        try:
            results = search.search(text, self.session)
        except ParseException, err:
            error_msg = _('Error in search string at column %s') % err.column
        except (BaubleError, AttributeError, Exception, SyntaxError), e:
            logger.debug(traceback.format_exc())
            error_msg = _('** Error: %s') % utils.xml_safe(e)
            error_details_msg = utils.xml_safe(traceback.format_exc())

        if error_msg:
            bauble.gui.show_error_box(error_msg, error_details_msg)
            return

        # not error
        utils.clear_model(self.results_view)
        self.update_infobox()
        statusbar = bauble.gui.widgets.statusbar
        sbcontext_id = statusbar.get_context_id('searchview.nresults')
        statusbar.pop(sbcontext_id)
        if len(results) == 0:
            model = gtk.ListStore(str)
            msg = bold % cgi.escape(
                _('Couldn\'t find anything for search: "%s"') % text)
            model.append([msg])
            self.results_view.set_model(model)
        else:
            if len(results) > 5000:
                msg = _('This query returned %s results.  It may take a '
                        'long time to get all the data. Are you sure you '
                        'want to continue?') % len(results)
                if not utils.yes_no_dialog(msg):
                    return
            statusbar.push(sbcontext_id, _("Retrieving %s search "
                                           "results...") % len(results))
            try:
                # don't bother with a task if the results are small,
                # this keeps the screen from flickering when the main
                # window is set to a busy state
                import time
                start = time.time()
                if len(results) > 1000:
                    self.populate_results(results)
                else:
                    task = self._populate_worker(results)
                    while True:
                        try:
                            task.next()
                        except StopIteration:
                            break
                logger.debug(time.time() - start)
            except StopIteration:
                return
            else:
                statusbar.pop(sbcontext_id)
                statusbar.push(sbcontext_id,
                               _("%s search results") % len(results))
                self.results_view.set_cursor(0)
                gobject.idle_add(lambda: self.results_view.scroll_to_cell(0))

        self.update_notes()

    def remove_children(self, model, parent):
        """
        Remove all children of some parent in the model, reverse
        iterate through them so you don't invalidate the iter
        """
        while model.iter_has_child(parent):
            nkids = model.iter_n_children(parent)
            child = model.iter_nth_child(parent, nkids-1)
            model.remove(child)

    def on_test_expand_row(self, view, treeiter, path, data=None):
        '''
        Look up the table type of the selected row and if it has
        any children then add them to the row
        '''
        expand = False
        model = view.get_model()
        row = model.get_value(treeiter, 0)
        view.collapse_row(path)
        self.remove_children(model, treeiter)
        try:
            kids = self.view_meta[type(row)].get_children(row)
            if len(kids) == 0:
                return True
        except saexc.InvalidRequestError, e:
            logger.debug(utils.utf8(e))
            model = self.results_view.get_model()
            for found in utils.search_tree_model(model, row):
                model.remove(found)
            return True
        except Exception, e:
            logger.debug(utils.utf8(e))
            logger.debug(traceback.format_exc())
            return True
        else:
            self.append_children(model, treeiter, kids)
            return False

    def populate_results(self, results, check_for_kids=False):
        """
        Adds results to the search view in a task.

        :param results: a list or list-like object
        :param check_for_kids: only used for testing
        """
        bauble.task.queue(self._populate_worker(results, check_for_kids))

    def _populate_worker(self, results, check_for_kids=False):
        """
        Generator function for adding the search results to the
        model. This method is usually called by self.populate_results()
        """
        nresults = len(results)
        model = gtk.TreeStore(object)
        model.set_default_sort_func(lambda *args: -1)
        model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
        utils.clear_model(self.results_view)

        groups = []

        # sort by type so that groupby works properly
        results = sorted(results, key=lambda x: type(x))

        for key, group in itertools.groupby(results, key=lambda x: type(x)):
            # return groups by type and natural sort each of the
            # groups by their strings
            groups.append(sorted(group, key=utils.natsort_key, reverse=True))

        # sort the groups by type so we more or less always get the
        # results by type in the same order
        groups = sorted(groups, key=lambda x: type(x[0]), reverse=True)

        chunk_size = 100
        update_every = 200
        steps_so_far = 0

        # iterate over slice of size "steps", yield after adding each
        # slice to the model
        #for obj in itertools.islice(itertools.chain(*groups), 0,None, steps):
        #for obj in itertools.islice(itertools.chain(results), 0,None, steps):

        added = set()
        for obj in itertools.chain(*groups):
            if obj in added:  # only add unique object
                continue
            else:
                added.add(obj)
            parent = model.prepend(None, [obj])
            obj_type = type(obj)
            if check_for_kids:
                kids = self.view_meta[obj_type].get_children(obj)
                if len(kids) > 0:
                    model.prepend(parent, ['-'])
            elif self.view_meta[obj_type].children is not None:
                model.prepend(parent, ['-'])
            #steps_so_far += chunk_size
            steps_so_far += 1
            if steps_so_far % update_every == 0:
                percent = float(steps_so_far)/float(nresults)
                if 0 < percent < 1.0:
                    bauble.gui.progressbar.set_fraction(percent)
                yield
        self.results_view.freeze_child_notify()
        self.results_view.set_model(model)
        self.results_view.thaw_child_notify()

    def append_children(self, model, parent, kids):
        """
        append object to a parent iter in the model

        :param model: the model the append to
        :param parent:  the parent gtk.TreeIter
        :param kids: a list of kids to append
        @return: the model with the kids appended
        """
        check(parent is not None, "append_children(): need a parent")
        for k in kids:
            i = model.append(parent, [k])
            if self.view_meta[type(k)].children is not None:
                model.append(i, ["_dummy"])
        return model

    def cell_data_func(self, col, cell, model, treeiter):
        path = model.get_path(treeiter)
        tree_rect = self.results_view.get_visible_rect()
        cell_rect = self.results_view.get_cell_area(path, col)
        if cell_rect.y > tree_rect.height:
            # only update the cells if they're visible...this
            # drastically speeds up populating the view with large
            # datasets
            return
        value = model[treeiter][0]
        if isinstance(value, basestring):
            cell.set_property('markup', value)
        else:
            # if the value isn't part of a session then add it to the
            # view's session so that we can access its child
            # properties...this usually happens when one of the
            # ViewMeta's get_children() functions return a list of
            # object who's session was closed...we add it here for
            # performance reasons so we only add it once it's visible
            if not object_session(value):
                if value in self.session:
                    # expire the object in the session with the same key
                    self.session.expire(value)
                else:
                    self.session.add(value)
            try:
                func = self.view_meta[type(value)].markup_func
                if func is not None:
                    r = func(value)
                    if isinstance(r, (list, tuple)):
                        main, substr = r
                    else:
                        main = r
                        substr = '(%s)' % type(value).__name__
                else:
                    main = utils.xml_safe(str(value))
                    substr = '(%s)' % type(value).__name__
                cell.set_property(
                    'markup', '%s\n%s' %
                    (_mainstr_tmpl % utils.utf8(main),
                     _substr_tmpl % utils.utf8(substr)))

            except (saexc.InvalidRequestError, TypeError), e:
                logger.warning(
                    'bauble.view.SearchView.cell_data_func(): \n%s' % e)

                def remove():
                    model = self.results_view.get_model()
                    self.results_view.set_model(None)  # detach model
                    for found in utils.search_tree_model(model, value):
                        model.remove(found)
                    self.results_view.set_model(model)
                gobject.idle_add(remove)

    def get_expanded_rows(self):
        '''
        return all the rows in the model that are expanded
        '''
        expanded_rows = []
        expand = lambda view, path: \
            expanded_rows.append(gtk.TreeRowReference(view.get_model(), path))
        self.results_view.map_expanded_rows(expand)
        # seems to work better if we passed the reversed rows to
        # self.expand_to_all_refs
        expanded_rows.reverse()
        return expanded_rows

    def expand_to_all_refs(self, references):
        '''
        :param references: a list of TreeRowReferences to expand to

        Note: This method calls get_path() on each
        gtk.TreeRowReference in <references> which apparently
        invalidates the reference.
        '''
        for ref in references:
            if ref.valid():
                self.results_view.expand_to_path(ref.get_path())

    def on_view_button_release(self, view, event, data=None):
        """right-mouse-button release.

        Popup a context menu on the selected row.
        """
        if event.button != 3:
            return False  # if not right click then leave

        selected = self.get_selected_values()
        if not selected:
            return
        selected_types = set(map(type, selected))
        if len(selected_types) > 1:
            # issue #31: currently we only show the menu when all objects
            # are of the same type. we could also show a common menu in case
            # the selection is of different types.
            return False
        selected_type = selected_types.pop()

        if not self.view_meta[selected_type].actions:
            # no actions
            return True

        # issue #31: ** important ** we need a common menu for all types
        # that can be merged with the specific menu for the selection,
        # e.g. provide a menu with a "Tag" action so you can tag
        # everything...or we could just ignore this and add "Tag" to all of
        # our action lists
        menu = None
        try:
            menu = self.context_menu_cache[selected_type]
        except KeyError:
            menu = gtk.Menu()
            for action in self.view_meta[selected_type].actions:
                logger.debug('path: %s' %  action.get_accel_path())
                item = action.create_menu_item()

                def on_activate(item, cb):
                    result = False
                    try:
                        # have to get the selected values again here
                        # because for some unknown reason using the
                        # "selected" variable from the parent scope
                        # will give us the objects but they won't be
                        # in an session...maybe it's a thread thing
                        values = self.get_selected_values()
                        result = cb(values)
                    except Exception, e:
                        msg = utils.xml_safe(str(e))
                        tb = utils.xml_safe(traceback.format_exc())
                        utils.message_details_dialog(
                            msg, tb, gtk.MESSAGE_ERROR)
                        logger.warning(traceback.format_exc())
                    if result:
                        self.reset_view()

                item.connect('activate', on_activate, action.callback)
                menu.append(item)
            self.context_menu_cache[selected_type] = menu

        # enable/disable the menu items depending on the selection
        for action in self.view_meta[selected_type].actions:
            action.enabled = (len(selected) > 1 and action.multiselect) or \
                (len(selected) <= 1 and action.singleselect)

        menu.popup(None, None, None, event.button, event.time)
        return True

    def reset_view(self):
        """
        Expire all the children in the model, collapse everything,
        reexpand the rows to the previous state where possible and
        update the infobox.
        """
        model, paths = self.results_view.get_selection().get_selected_rows()
        ref = None
        try:
            # try to get the reference to the selected object, if the
            # object has been deleted then we won't try to reselect it later
            ref = gtk.TreeRowReference(model, paths[0])
        except:
            pass

        self.session.expire_all()

        # the invalidate_str_cache() method are specific to Species
        # and Accession right now....it's a bit of a hack since there's
        # no real interface that the method complies to...but it does
        # fix our string caching issues
        def invalidate_cache(model, path, treeiter, data=None):
            obj = model[path][0]
            if hasattr(obj, 'invalidate_str_cache'):
                obj.invalidate_str_cache()
        model.foreach(invalidate_cache)
        expanded_rows = self.get_expanded_rows()
        self.results_view.collapse_all()
        # expand_to_all_refs will invalidate the ref so get the path first
        if not ref:
            return
        path = None
        if ref.valid():
            path = ref.get_path()
        self.expand_to_all_refs(expanded_rows)
        self.results_view.set_cursor(path)

    def on_view_row_activated(self, view, path, column, data=None):
        '''
        expand the row on activation
        '''
        logger.debug("on_view_row_activated %s %s %s %s"
                     % (view, path, column, data))
        view.expand_row(path, False)

    def create_gui(self):
        '''
        create the interface
        '''
        # create the results view and info box
        self.results_view = self.widgets.results_treeview

        self.results_view.set_headers_visible(False)
        self.results_view.set_rules_hint(True)
        self.results_view.set_fixed_height_mode(True)

        selection = self.results_view.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.results_view.set_rubber_banding(True)

        renderer = gtk.CellRendererText()
        renderer.set_fixed_height_from_font(2)
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn("Name", renderer)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_cell_data_func(renderer, self.cell_data_func)
        self.results_view.append_column(column)

        # view signals
        self.results_view.connect("cursor-changed", self.on_cursor_changed)
        self.results_view.connect("test-expand-row",
                                  self.on_test_expand_row)
        self.results_view.connect("button-release-event",
                                  self.on_view_button_release)

        def on_press(view, event):
            """Ignore the mouse right-click event.

            This makes sure that we don't remove the multiple selection
            when clicking a mouse button.
            """
            if event.button == 3:
                if (event.get_state() & gtk.gdk.CONTROL_MASK) == 0:
                    path, _, _, _ = view.get_path_at_pos(int(event.x), int(event.y))
                    if not view.get_selection().path_is_selected(path):
                        return False
                return True
            else:
                return False

        self.results_view.connect("button-press-event", on_press)

        self.results_view.connect("row-activated",
                                  self.on_view_row_activated)

        # this group doesn't need to be added to the main window with
        # gtk.Window.add_accel_group since the group will be added
        # automatically when the view is set
        self.accel_group = gtk.AccelGroup()
        self.installed_accels = []

        self.pane = self.widgets.search_hpane
        self.picpane = self.widgets.search_h2pane

        # initialize the notes expander and tree view
        self._notes_expanded = False

        def on_expanded(expander, *args):
            self._notes_expanded = expander.props.expanded
            if not self._notes_expanded:
                # don't use the position property so that when the
                # expander is collapsed then the top pane will
                # maximize itself
                self.widgets.search_vpane.props.position_set = False

        self.widgets.notes_expander.connect_after('activate', on_expanded)
        self.init_notes_treeview()

        vbox = self.widgets.search_vbox
        self.widgets.remove_parent(vbox)
        self.pack_start(vbox)

    def on_notes_size_allocation(self, treeview, allocation, column, cell):
        """
        Set the wrap width according to the widgth of the treeview
        """
        # This code came from the PyChess project
        otherColumns = (c for c in treeview.get_columns() if c != column)
        newWidth = allocation.width - sum(c.get_width() for c in otherColumns)
        newWidth -= treeview.style_get_property("horizontal-separator") * 2
        if cell.props.wrap_width == newWidth or newWidth <= 0:
            return
        cell.props.wrap_width = newWidth
        store = treeview.get_model()
        treeiter = store.get_iter_first()
        while treeiter and store.iter_is_valid(treeiter):
            store.row_changed(store.get_path(treeiter), treeiter)
            treeiter = store.iter_next(treeiter)
            treeview.set_size_request(0, -1)

    def init_notes_treeview(self):
        def cell_data_func(col, cell, model, treeiter, prop):
            row = model[treeiter][0]
            val = getattr(row, prop)
            if val:
                if prop == 'date':
                    format = prefs.prefs[prefs.date_format_pref]
                    val = val.strftime(format)
                cell.set_property('text', utils.utf8(val))
            else:
                cell.set_property('text', '')

        date_cell = self.widgets.date_cell
        date_col = self.widgets.date_column
        date_col.set_cell_data_func(date_cell, cell_data_func, 'date')

        category_cell = self.widgets.category_cell
        category_col = self.widgets.category_column
        category_col.set_cell_data_func(category_cell, cell_data_func,
                                        'category')

        name_cell = self.widgets.name_cell
        name_col = self.widgets.name_column
        name_col.set_cell_data_func(name_cell, cell_data_func, 'user')

        note_cell = self.widgets.note_cell
        note_col = self.widgets.note_column
        note_col.set_cell_data_func(note_cell, cell_data_func, 'note')

        # TODO: need to better test to make sure this wraps the text properly
        self.widgets.notes_treeview.\
            connect_after("size-allocate", self.on_notes_size_allocation,
                          note_col, note_cell)


class StringColumn(gtk.TreeViewColumn):

    """
    A generic StringColumn for use in a gtk.TreeView.

    This code partially based on the StringColumn from the Quidgets
    project (http://launchpad.net/quidgets)
    """
    def __init__(self, title, format_func=None, **kwargs):
        self.renderer = gtk.CellRendererText()
        super(StringColumn, self).__init__(title, self.renderer, **kwargs)
        self.renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        if format_func:
            self.set_cell_data_func(self.renderer, self.cell_data_func,
                                    format_func)

    def cell_data_func(self, column, cell, model, treeiter, format):
        value = format(model[treeiter])
        cell.set_property('text', value)


class HistoryView(pluginmgr.View):
    """Show the tables row in the order they were last updated
    """
    def __init__(self):
        super(HistoryView, self).__init__()
        self.init_gui()

    def init_gui(self):
        self.treeview = gtk.TreeView()
        #self.treeview.set_fixed_height_mode(True)
        columns = [(_('Timestamp'), 0), (_('Operation'), 1),
                   (_('User'), 2), (_('Table'), 3), (_('Values'), 4)]
        for name, index in columns:
            column = StringColumn(name, text=index)
            column.set_sort_column_id(index)
            column.set_expand(False)
            column.props.sizing = gtk.TREE_VIEW_COLUMN_AUTOSIZE
            column.set_resizable(True)
            column.renderer.set_fixed_height_from_font(1)
            self.treeview.append_column(column)
        sw = gtk.ScrolledWindow()
        sw.add(self.treeview)
        self.pack_start(sw)

    def populate_history(self, arg):
        """
        Add the history items to the view.
        """
        session = db.Session()
        utils.clear_model(self.treeview)
        model = gtk.ListStore(str, str, str, str, str)
        for item in session.query(db.History).\
                order_by(db.History.timestamp.desc()).all():
            model.append([item.timestamp, item.operation, item.user,
                          item.tablename, item.values])
        self.treeview.set_model(model)
        session.close()


class HistoryCommandHandler(pluginmgr.CommandHandler):

    def __init__(self):
        super(HistoryCommandHandler, self).__init__()
        self.view = None

    command = 'history'

    def get_view(self):
        if not self.view:
            self.view = HistoryView()
        return self.view

    def __call__(self, cmd, arg):
        self.view.populate_history(arg)


pluginmgr.register_command(HistoryCommandHandler)


def select_in_search_results(obj):
    """
    :param obj: the object the select
    @returns: a gtk.TreeIter to the selected row

    Search the tree model for obj if it exists then select it if not
    then add it and select it.

    The the obj is not in the model then we add it.
    """
    check(obj is not None, 'select_in_search_results: arg is None')
    view = bauble.gui.get_view()
    if not isinstance(view, SearchView):
        return None
    model = view.results_view.get_model()
    found = utils.search_tree_model(model, obj)
    row_iter = None
    if len(found) > 0:
        row_iter = found[0]
    else:
        row_iter = model.append(None, [obj])
        model.append(row_iter, ['-'])
    view.results_view.set_cursor(model.get_path(row_iter))
    return row_iter


class DefaultCommandHandler(pluginmgr.CommandHandler):

    def __init__(self):
        super(DefaultCommandHandler, self).__init__()
        self.view = None

    command = [None]

    def get_view(self):
        if self.view is None:
            self.view = SearchView()
        return self.view

    def __call__(self, cmd, arg):
        self.view.search(arg)
