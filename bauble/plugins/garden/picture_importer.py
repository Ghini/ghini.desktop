# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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
logger = logging.getLogger(__name__)

from gi.repository import Gtk
from gi.repository import GObject
from gi.repository import GdkPixbuf
import threading
import glib
import re
import os.path
from bauble import pluginmgr, db, utils
from sqlalchemy.orm.exc import NoResultFound

from bauble.editor import (GenericEditorView, GenericEditorPresenter)

accno_re = re.compile(r'([12][0-9][0-9][0-9]\.[0-9][0-9][0-9][0-9])(?:\.([0-9]+))?')
species_re = re.compile(r'([A-Z][a-z]+(?: [a-z-]*)?)')
picname_re = re.compile(r'([A-Z]+[0-9]+)')
number_re = re.compile(r'([0-9]+)')

def decode_parts(name, acc_format=None):
    """return the dictionary of parts in name

    name is matched against the basic concepts in a plant description, like
    its accession or species.  all matching parts are used to construct a
    dictionary, which is then returned.

    accession, defaults to None,
    plant, defaults to 1,
    seq, defaults to 1,
    species, defaults to Zzz

    """

    # look for anything looking like (and remove it), in turn: species name,
    # accession number with optional plant number, original picture name,
    # some other number overruling the original picture name.

    #only scan name part, ignore location
    path, name = os.path.split(name)

    result = {'accession': None,
              'plant': '1',
              'seq': '1',
              'species': 'Zzz'}

    if acc_format is None:
        use_accno_re = accno_re
    else:
        exp_str = acc_format.replace('.', '\.').replace('#', "[0-9]")
        exp_str = "(%s)(?:\.([0-9]+))?" % exp_str
        use_accno_re = re.compile(exp_str)
    for key, exp in [('accession', use_accno_re),
                     ('species', species_re),
                     ('seq', picname_re),
                     ('seq', number_re)]:
        match = exp.search(name)
        if match:
            value = match.group(1)
            if not value:
                continue
            if key == 'seq':
                value = re.sub(r'([A-Z]+0*)', '', value)
            result[key] = value
            if key == 'accession' and match.group(2):
                result['plant'] = match.groups()[1]
            name = name.replace(match.group(0), '')
    if result['accession'] is None:
        return None
    return result


def none(function, *args):
    '''invoke function but drop return value'''

    function(*args)
    return None


class ListStoreHandler(logging.Handler):
    def __init__(self, container, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container = container
        GObject.idle_add(none, self.container.clear)

    def emit(self, record):
        msg = self.format(record)
        stock = {11: 'gtk-directory',
                 12: 'gtk-file',
                 13: 'gtk-new', }[record.levelno]
        GObject.idle_add(none, self.container.append, [stock, msg])


def query_session_new(session, cls, **kwargs):
    for i in session.new:
        found = False
        if type(i) == cls:
            found = True
            for k, v in list(kwargs.items()):
                if getattr(i, k) != v:
                    found = False
        if found:
            return i


use_me_col = 0
filename_col = 1
accno_col = 2
binomial_col = 3
thumbnail_col = 4
iseditable_col = 5
orig_accno_col = 6
edited_accno_col = 7
full_filename_col = 8
orig_binomial_col = 9
edited_binomial_col = 10


class PictureImporterPresenter(GenericEditorPresenter):
    widget_to_field_map = {
        'accno_entry': 'accno_format',
        'filepath_entry': 'filepath',
        'recurse_checkbutton': 'recurse'}

    def __init__(self, model, view, **kwargs):
        kwargs['refresh_view'] = True
        super().__init__(model, view, **kwargs)
        self.panes = [getattr(self.view.widgets, 'box_define'),
                      getattr(self.view.widgets, 'box_review'),
                      getattr(self.view.widgets, 'box_log'),]
        self.review_liststore = self.view.widgets.review_liststore
        self.running_thread = None
        self.keep_running = None
        self.show_visible_pane()
        self.view.widgets.use_tvc.set_sort_column_id(use_me_col)
        self.view.widgets.filename_tvc.set_sort_column_id(filename_col)
        self.view.widgets.accno_tvc.set_sort_column_id(accno_col)
        self.view.widgets.binomial_tvc.set_sort_column_id(binomial_col)
        self.view.widgets.iseditable_tvc.set_sort_column_id(iseditable_col)

        from bauble.plugins.garden import init_location_comboentry, Location
        def on_location_select(location):
            self.model.location = location.code

        init_location_comboentry(self, self.view.widgets.location_combobox,
                                 on_location_select)

    def show_visible_pane(self):
        for n, i in enumerate(self.panes):
            i.set_visible(n == self.model.visible_pane)
        self.view.widgets.button_prev.set_sensitive(self.model.visible_pane > 0)
        self.view.widgets.button_next.set_sensitive(self.model.visible_pane < len(self.panes) - 1)
        self.view.widgets.button_ok.set_sensitive(False)
        self.should_commit = False  # reset inconditionally when changing pane
        if self.running_thread:
            self.keep_running = False
            if self.running_thread.name == 'do_import':
                self.lock.release()
            self.running_thread.join()
            self.running_thread = None
        if self.model.visible_pane == 1:
            self.session.rollback()  # clean up session

    def load_pixbufs(self):
        # to be run in different thread - or you're blocking the gui
        for fname, path in self.pixbufs_to_load:
            if not self.keep_running:
                return
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(fname)
            try:
                pixbuf = pixbuf.apply_embedded_orientation()
                scale_x = pixbuf.get_width() / 144
                scale_y = pixbuf.get_height() / 144
                scale = max(scale_x, scale_y, 1)
                x = int(pixbuf.get_width() / scale)
                y = int(pixbuf.get_height() / scale)
                pixbuf = pixbuf.scale_simple(x, y, GdkPixbuf.InterpType.BILINEAR)
                def set_thumbnail(store, path, col, value):
                    store[path][col] = value
                GObject.idle_add(set_thumbnail, self.review_liststore, path, thumbnail_col, pixbuf)
            except glib.GError as e:
                logger.debug("picture %s caused glib.GError %s" %
                             (fname, e))
            except Exception as e:
                logger.warning("picture %s caused Exception %s:%s" %
                               (fname, type(e), e))

    def add_rows(self, arg, dirname, fnames):
        for name in fnames:
            d = decode_parts(name, self.model.accno_format)
            if d is None:
                continue
            from bauble.plugins.garden import Plant
            complete_plant_code = d['accession'] + Plant.get_delimiter() + d['plant']
            row = [True, name, complete_plant_code, d['species'], None, False, complete_plant_code, complete_plant_code,
                   os.path.join(dirname, name), d['species'], d['species']]
            self.pixbufs_to_load.append((os.path.join(dirname, name), (len(self.review_liststore), )))
            self.review_liststore.append(row)

    def on_cellrenderertext_edited(self, widget, path, new_text, *args, **kwargs):
        if widget == self.view.widgets.accno_crtext:
            self.review_liststore[path][accno_col] = self.review_liststore[path][edited_accno_col] = new_text
        elif widget == self.view.widgets.binomial_crtext:
            self.review_liststore[path][binomial_col] = self.review_liststore[path][edited_binomial_col] = new_text

    def on_use_crtoggle_toggled(self, column_widget, path):
        self.review_liststore[path][use_me_col] = not self.review_liststore[path][use_me_col]

    def on_edit_crtoggle_toggled(self, column_widget, path):
        self.review_liststore[path][iseditable_col] = not self.review_liststore[path][iseditable_col]
        if not self.review_liststore[path][iseditable_col]:  # let's restore original
            self.review_liststore[path][accno_col] = self.review_liststore[path][orig_accno_col]
            self.review_liststore[path][binomial_col] = self.review_liststore[path][orig_binomial_col]
        else:  # otherwise: restore last edit
            self.review_liststore[path][accno_col] = self.review_liststore[path][edited_accno_col]
            self.review_liststore[path][binomial_col] = self.review_liststore[path][edited_binomial_col]

    def do_import(self):  # step 2
        session = db.Session()
        handler = ListStoreHandler(self.view.widgets.log_liststore)
        logger.addHandler(handler)
        self.view.widgets.log_treeview.scroll_to_point(0, 0)
        from bauble.plugins.plants import (Genus, Species)
        from bauble.plugins.garden import (Location, Accession, Plant, PlantNote)
        # make sure selected location exists
        if self.model.location is None:
            self.model.location = 'imported'
        location = session.query(Location).filter_by(code=self.model.location).first()
        if location is not None:
            logger.log(11, 'location %s already in database' % (location, ))
        else:
            location = Location(code=self.model.location)
            session.add(location)
            logger.log(13, 'created new location %s' % (location, ))

        # iterate over liststore content
        for row in self.review_liststore:
            if not self.keep_running:
                break
            if not row[use_me_col]:
                continue
            # get unicode strings from row
            epgn, epsp = str(row[binomial_col] + ' sp').split(' ')[:2]
            filename = str(row[filename_col])
            complete_plant_code = str(row[accno_col])
            accession_code, plant_code = complete_plant_code.rsplit(Plant.get_delimiter(), 1)

            # create or retrieve genus and species
            genus = session.query(Genus).filter_by(epithet=epgn).one()
            species = session.query(Species).filter_by(genus=genus, epithet=epsp).first()
            if species is not None:
                logger.log(11, 'species %s %s already in database' % (epgn, epsp))
            else:
                species = query_session_new(session, Species, genus=genus, epithet=epsp)
                if species is None:
                    species = Species(genus=genus, epithet=epsp)
                    session.add(species)
                    logger.log(13, 'created species %s %s' % (epgn, epsp))
                else:
                    logger.log(12, 'reusing new species %s %s' % (epgn, epsp))

            # create or retrieve accession (needs species)
            accession = session.query(Accession).filter_by(code=accession_code).first()
            if accession is not None:
                logger.log(11, 'accession %s already in database' % (accession_code))
            else:
                accession = query_session_new(session, Accession, code=accession_code)
                if accession is None:
                    accession = Accession(species=species, code=accession_code, quantity_recvd=1)
                    session.add(accession)
                    logger.log(13, 'created accession %s for species %s %s' % (accession_code, epgn, epsp))
                else:
                    logger.log(12, 'reusing new accession %s' % (accession_code))

            # create or retrieve plant (needs: accession, location)
            plant = session.query(Plant).filter_by(accession=accession, code=plant_code).first()
            if plant is not None:
                logger.log(11, 'plant %s already in database' % (complete_plant_code))
            else:
                plant = query_session_new(session, Plant, accession=accession, code=plant_code)
                if plant is None:
                    plant = Plant(accession=accession, quantity=1, location=location, code=plant_code)
                    session.add(plant)
                    logger.log(13, 'created plant %s' % (complete_plant_code))
                else:
                    logger.log(12, 'reusing new plant %s' % (complete_plant_code))

            # copy picture file - possibly renaming it
            utils.copy_picture_with_thumbnail(self.model.filepath, filename)

            # add picture note
            note = session.query(PlantNote).filter_by(plant=plant, note=filename, category='<picture>').first()
            if note is not None:
                logger.log(11, 'picture %s already in plant %s' % (filename, complete_plant_code))
            else:
                note = query_session_new(session, PlantNote, plant=plant, note=filename, category='<picture>')
                if note is None:
                    note = PlantNote(plant=plant, note=filename, category='<picture>', user='initial-import')
                    session.add(note)
                    logger.log(13, 'picture %s added to plant %s' % (filename, complete_plant_code))
                else:
                    logger.log(12, 'reusing new picture %s in plant %s' % (filename, complete_plant_code))
        logger.removeHandler(handler)
        self.view.widgets.button_ok.set_sensitive(self.keep_running is True)
        self.lock.acquire()
        if self.should_commit:
            session.commit()
        else:
            session.rollback()
        self.lock.release()

    def on_picture_importer_dialog_response(self, widget, response, **kwargs):
        self.keep_running = None

    def on_action_prev_activate(self, *args, **kwargs):
        self.model.visible_pane -= 1
        self.show_visible_pane()

    def on_action_next_activate(self, *args, **kwargs):
        self.model.visible_pane += 1
        self.show_visible_pane()
        if self.model.visible_pane == 1:  # let user review import
            self.review_liststore.clear()
            self.view.widgets.review_treeview.scroll_to_point(0, 0)
            self.pixbufs_to_load = []
            os.path.walk(self.model.filepath, self.add_rows, None)
            self.keep_running = True
            self.running_thread = threading.Thread(target=self.load_pixbufs, name='load_pixbufs')
            self.running_thread.start()
        elif self.model.visible_pane == 2:  # import as specified
            self.keep_running = True
            self.should_commit = False
            self.lock = threading.Lock()
            self.lock.acquire()
            self.running_thread = threading.Thread(target=self.do_import, name='do_import')
            self.running_thread.start()

    def show_gtk_stock_icons(self):
        '''this is just some code to show an overview of gtk stock name/image'''
        for i in Gtk.stock_list_ids():
            self.view.widgets.log_liststore.append([i, i])

    def on_action_cancel_activate(self, *args, **kwargs):
        if self.running_thread:
            self.keep_running = None  # any running thread will return soon
            if self.running_thread.name == 'do_import':
                self.lock.release()  # don't stop `do_import` at the lock
            self.running_thread.join()
            self.running_thread = None
        self.view.get_window().emit('response', Gtk.ResponseType.DELETE_EVENT)

    def on_action_ok_activate(self, *args, **kwargs):
        # OK is set active only in do_import.  if we're here, means that
        # do_import has been running and is now waiting for us at the lock.
        self.should_commit = True
        self.lock.release()
        self.running_thread.join()  # do_import is now committing
        self.running_thread = None
        self.view.get_window().emit('response', Gtk.ResponseType.OK)

    def on_action_browse_activate(self, *args, **kwargs):
        text = _('Select pictures source directory')
        parent = None
        action = Gtk.FileChooserAction.SELECT_FOLDER
        buttons = (_('Cancel'), Gtk.ResponseType.CANCEL, _('Ok'), Gtk.ResponseType.ACCEPT, )
        last_folder = self.model.filepath
        target = 'filepath_entry'
        self.view.run_file_chooser_dialog(text, parent, action, buttons, last_folder, target)

class PictureImporterTool(pluginmgr.Tool):
    category = _('Import')
    label = _('Picture Collection')
    model = type('Model', (object,),
                 {'visible_pane': 0,
                  'filepath': '',
                  'accno_format': '####.####',
                  'recurse': False,
                  'location': None,
                  'rows': [],
                  'log': []})
    import os.path
    from bauble import paths
    glade_path = os.path.join(paths.lib_dir(), "plugins", "garden",
                              "picture_importer.glade")

    @classmethod
    def start(cls):
        cls.model.visible_pane = 0
        view = GenericEditorView(
            cls.glade_path,
            parent=None,
            root_widget_name='picture_importer_dialog')
        presenter = PictureImporterPresenter(cls.model, view)
        result = presenter.start()
        try:
            from bauble import gui
            gui.get_view().update()
        except Exception as e:
            pass
        return True
