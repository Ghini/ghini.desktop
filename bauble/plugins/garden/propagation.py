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


cutting_type_values = {u'Nodal': _('Nodal'),
                       u'InterNodal': _('Internodal'),
                       u'Other': _('Other')}

tip_values = {u'Intact': _('Intact'),
              u'Removed': _('Removed'),
              u'None': _('None')}

leaves_values = {u'Intact': _('Intact'),
                 u'Removed': _('Removed'),
                 u'None': _('None')}

flower_buds_values = {u'Removed': _('Removed'),
                      u'None': _('None')}

wound_values = {u'No': _('No'),
                u'Single': _('Singled'),
                u'Double': _('Double'),
                u'Slice': _('Slice')}

hormone_values = {u'Liquid': _('Liquid'),
                  u'Powder': _('Powder'),
                  u'No': _('No')}


class PropCutting(db.Base):
    """
    A cutting
    """
    __tablename__ = 'prop_cutting'
    cutting_type = Column(types.Enum(values=cutting_type_values.keys()))
    tip = Column(types.Enum(values=tip_values.keys()))
    leaves = Column(types.Enum(values=leaves_values.keys()))
    leaves_reduced_pct = Column(Integer)
    length = Column(Integer)
    length_units = Column(Unicode)

    # single/double/slice
    wound = Column(types.Enum(values=wound_values.keys()))

    # removed/None
    flower_buds = Column(types.Enum(values=flower_buds_values.keys()))

    fungal_soak_sol = Column(Unicode) # fungal soak solution

    #fungal_soak_sec = Column(Boolean)

    hormone = Column(Unicode) # power/liquid/None....solution

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



class PropagationPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'acc_code_entry': 'code'}


    def __init__(self, parent, model, view, session):
        '''
        @param model: an instance of class Propagation
        @param view: an instance of PropagationEditorView
        '''
        super(PropagationPresenter, self).__init__(model, view)
        self.parent_ref = weakref.ref(parent)
        self.session = session

        self.init_translatable_combo('prop_type_combo', prop_type_values)
        self.init_translatable_combo('cutting_type_combo', cutting_type_values)
        self.init_translatable_combo('cutting_tip_combo', tip_values)
        self.init_translatable_combo('cutting_leaves_combo', leaves_values)
        self.init_translatable_combo('cutting_buds_combo', leaves_values)
        self.init_translatable_combo('cutting_wound_combo', wound_values)

        self.view.connect('prop_type_combo', 'changed',
                          self.on_prop_type_changed)




    def on_prop_type_changed(self, combo, *args):
        it = combo.get_active_iter()
        prop_type = combo.get_model()[it][0]
        debug(prop_type)

        prop_box_map = {u'Seed': self.view.widgets.seed_box,
                        u'UnrootedCutting': self.view.widgets.cutting_box,
                        u'Other': self.view.widgets.prop_notes_box}

        parent = self.view.widgets.prop_box_parent
        prop_box = prop_box_map[prop_type]
        child = parent.get_child()
        if child:
            parent.remove(child)
        self.view.widgets.remove_parent(prop_box)
        parent.add(prop_box)

