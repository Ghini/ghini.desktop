# -*- coding: utf-8 -*-
#
# propagation module
#

import sys
import re
import os
import weakref
import traceback
from random import random
from datetime import datetime
import xml.sax.saxutils as saxutils

import gtk
import gobject
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import SQLError

import bauble
import bauble.db as db
from bauble.error import check
import bauble.utils as utils
import bauble.paths as paths
import bauble.editor as editor
from bauble.utils.log import debug
from bauble.prefs import prefs
from bauble.error import CommitException
import bauble.types as types
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
     select_in_search_results, Action

prop_type_values = {u'Seed': _("Seed"),
                    u'UnrootedCutting': _('Unrooted cutting'),
                    u'Other': _('Other')}


class Propagation(db.Base):
    """
    Propagation
    """
    __tablename__ = 'propagation'
    #recvd_as = Column(Unicode(10)) # seed, urcu, other
    #recvd_as_other = Column(UnicodeText) # ** maybe this should be in the notes
    prop_type = Column(types.Enum(values=prop_type_values.keys()),
                        default=u'UnrootedCutting')
    notes = Column(UnicodeText)

    accession_id = Column(Integer, ForeignKey('accession.id'),
                          nullable=False)

    def __str__(self):
        # what would the string be...???
        # cuttings of self.accession.species_str() and accessin number
        return repr(self)



class PropRooted(db.Base):
    """
    Rooting dates for cutting
    """
    __tablename__ = 'prop_cutting_rooted'
    date = Column(Date)
    quantity = Column(Integer)
    cutting_id = Column(Integer, ForeignKey('prop_cutting.id'), nullable=False)


class PropCutting(db.Base):
    """
    A cutting
    """
    __tablename__ = 'prop_cutting'
    cutting_type = Column(Unicode)
    tip = Column(Unicode)
    leaves = Column(Unicode)
    leaves_reduced_pct = Column(Integer)
    length = Column(Integer)
    length_units = Column(Unicode)
    wounded = Column(Boolean)  # single/double/slice
    flower_buds = Column(Unicode) # removed/None
    fungal_soak_sol = Column(Unicode) # fungal soak solution
    fungal_soak_sec = Column(Boolean)
    hormone = Column(Unicode) # power/liquid....solution

    cover_type = Column(Unicode) # vispore, poly, plastic dome, poly bag

    bottom_heat_temp = Column(Integer) # temperature of bottom heat
    bottom_heat_unit = Column(Unicode) # F/C

    success = Column(Integer) # % of rooting took

    #aftercare = Column(UnicodeText) # same as propgation.notes

    propagation_id = Column(Integer, ForeignKey('propagation.id'),
                            nullable=False)


class PropSeed(db.Base):
    """
    """
    __tablename__ = 'prop_seed'
    pretreatment = Column(UnicodeText)
    nseeds = Column(Integer)
    date_sowed = Column(Date)

    container = Column(Unicode) # 4" pot plug tray, other
    compost = Column(Unicode) # seedling media, sphagnum, other

    # covered with #2 granite grit: no, yes, lightly heavily
    covered = Column(Unicode)

    # not same as location table, glasshouse(bottom heat, no bottom
    # heat), polyhouse, polyshade house, fridge in polybag
    location = Column(Unicode)

    # TODO: do we need multiple moved to->moved from and date fields
    moved_from = Column(Unicode)
    moved_to = Column(Unicode)
    moved_date = Column(Unicode)

    germ_date = Column(Date)

    nseedling = Column(Integer) # number of seedling
    germ_pct = Column(Integer) # % of germination
    date_planted = Column(Date)

    propagation_id = Column(Integer, ForeignKey('propagation.id'),
                            nullable=False)



class PropagationEditorView(editor.GenericEditorView):
    """
    """

    _tooltips = {}

    def __init__(self, parent=None):
        """
        """
        super(PropagationEditorView, self).\
            __init__(os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                  'prop_editor.glade'),
                     parent=parent)

    def get_window(self):
        """
        """
        return self.widgets.prop_dialog


    def start(self):
        return self.get_window().run()


class PropagationEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'acc_code_entry': 'code'}

    def __init__(self, model, view):
        '''
        @param model: an instance of class Propagation
        @param view: an instance of PropagationEditorView
        '''
        super(PropagationEditorPresenter, self).__init__(model, view)
        self.session = object_session(model)

        self.init_translatable_combo('prop_type_combo', prop_type_values)
        self.view.connect('prop_type_combo', 'changed',
                          self.on_prop_type_changed)


    def on_prop_type_changed(self, combo, *args):
        it = combo.get_active_iter()
        prop_type = combo.get_model()[it][0]
        debug(prop_type)


    def dirty(self):
        pass

    def set_model_attr(self, field, value, validator=None):
        """
        Set attributes on the model and update the GUI as expected.
        """
        #debug('set_model_attr(%s, %s)' % (field, value))
        super(PropagationEditorPresenter, self).set_model_attr(field, value,
                                                               validator)

    def refresh_sensitivity(self):
        pass

    def refresh_view(self):
        pass

    def start(self):
        r = self.view.start()
        return r


class PropagationEditor(editor.GenericModelViewPresenterEditor):

    label = _('Propagation')
    mnemonic_label = _('_Propagation')

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)


    def __init__(self, model=None, parent=None):
        '''
        @param model: Propagation instance or None
        @param parent: the parent widget
        '''
        # the view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        if model is None:
            model = Propagation()
        super(PropagationEditor, self).__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = PropagationEditorView(parent=self.parent)
        self.presenter = PropagationEditorPresenter(self.model, view)

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set the default focus
        # if self.model.species is None:
        #     view.widgets.acc_species_entry.grab_focus()
        # else:
        #     view.widgets.acc_code_entry.grab_focus()


    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:
                msg = _('Error committing changes.\n\n%s') % \
                      utils.xml_safe_utf8(unicode(e.orig))
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') \
                        % utils.xml_safe_utf8(e)
                debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = PropagationEditor(parent=self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True


    def start(self):
        # from bauble.plugins.plants.species_model import Species
        # if self.session.query(Species).count() == 0:
        #     msg = _('You must first add or import at least one species into '\
        #                 'the database before you can add accessions.')
        #     utils.message_dialog(msg)
        #     return

        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break

        self.session.close() # cleanup session
        self.presenter.cleanup()
        return self._committed
