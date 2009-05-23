#
# Family table definition
#

import os
import traceback

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import SQLError
from sqlalchemy.ext.associationproxy import association_proxy

import bauble
import bauble.db as db
from bauble.i18n import _
import bauble.pluginmgr as pluginmgr
import bauble.editor as editor
import bauble.utils.desktop as desktop
from datetime import datetime
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.types import Enum
from bauble.prefs import prefs

def edit_callback(value):
    """
    Family context menu callback
    """
    session = bauble.Session()
    e = FamilyEditor(model=session.merge(value))
    return e.start() != None


def add_genera_callback(value):
    """
    Family context menu callback
    """
    session = bauble.Session()
    e = GenusEditor(model=Genus(family=session.merge(value)))
    return e.start() != None


def remove_callback(family):
    """
    The callback function to remove a family from the family context menu.
    """
    from bauble.plugins.plants.genus import Genus
    session = bauble.Session()
    ngen = session.query(Genus).filter_by(family_id=family.id).count()
    safe_str = utils.xml_safe_utf8(str(family))
    if ngen > 0:
        msg = _('The family <i>%s</i> has %s genera.  Are you sure you want '
                'to remove it?') % (safe_str, ngen)
    else:
        msg = _("Are you sure you want to remove the family <i>%s</i>?") \
            % safe_str
    if not utils.yes_no_dialog(msg):
        return
    try:
        obj = session.query(Family).get(family.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    session.close()
    return True


family_context_menu = [(_('Edit'), edit_callback),
                       ('--', None),
                       (_('Add genera'), add_genera_callback),
                       ('--', None),
                       (_('Remove'), remove_callback)]


def family_markup_func(family):
    """
    return a string or object with __str__ method to use to markup
    text in the results view
    """
    return family


#
# Family
#
class Family(db.Base):
    """
    :Table name: family

    :Columns:
        *family*:
            The name if the family. Required.

        *qualifier*:
            The family qualifier.

            Possible values:
                * s. lat.: aggregrate family (senso lato)

                * s. str.: segregate family (senso stricto)

                * None: the None value

        *notes*:
            Free text notes about the family.

    :Properties:
        *synonyms*:
            An association to _synonyms that will automatically
            convert a Family object and create the synonym.

    :Constraints:
        The family table has a unique constraint on family/qualifier.
    """
    __tablename__ = 'family'
    __table_args__ = (UniqueConstraint('family', 'qualifier'), {})
    __mapper_args = {'order_by': ['family', 'qualifier']}

    # columns
    family = Column(String(45), nullable=False, index=True)

    # we use the blank string here instead of None so that the
    # contrains will work properly,
    qualifier = Column(Enum(values=['s. lat.', 's. str.', '']), default=u'')
    notes = Column(UnicodeText)

    # relations
    synonyms = association_proxy('_synonyms', 'synonym')
    genera = relation('Genus', backref='family', cascade='all, delete-orphan')
    _synonyms =  relation('FamilySynonym',
                          primaryjoin='FamilySynonym.family_id==Family.id',
                          cascade='all, delete-orphan', uselist=True,
                          backref='family')

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this family
    # get deleted if this family gets deleted
    __syn = relation('FamilySynonym',
                     primaryjoin='FamilySynonym.synonym_id==Family.id',
                     cascade='all, delete-orphan', uselist=True)

    def __str__(self):
        return Family.str(self)

    @staticmethod
    def str(family, qualifier=False):
        if family.family is None:
            return repr(family)
        else:
            return ' '.join([s for s in [family.family,
                                    family.qualifier] if s not in (None,'')])



class FamilySynonym(db.Base):
    """
    :Table name: family_synonyms

    :Columns:
        *family_id*:

        *synonyms_id*:

    :Properties:
        *synonyms*:

        *species*:
    """
    __tablename__ = 'family_synonym'
    __table_args__ = (UniqueConstraint('family_id', 'synonym_id'), {})

    # columns
    family_id = Column(Integer, ForeignKey('family.id'), nullable=False)
    synonym_id = Column(Integer, ForeignKey('family.id'), nullable=False)

    # relations
    synonym = relation('Family', uselist=False,
                       primaryjoin='FamilySynonym.synonym_id==Family.id')

    def __init__(self, synonym=None, **kwargs):
        # it is necessary that the first argument here be synonym for
        # the Family.synonyms association_proxy to work
        self.synonym = synonym
        super(FamilySynonym, self).__init__(**kwargs)

    def __str__(self):
        return Family.str(self.synonym)


#
# late imports
#
from bauble.plugins.plants.genus import Genus, GenusEditor


class FamilyEditorView(editor.GenericEditorView):

    syn_expanded_pref = 'editor.family.synonyms.expanded'

    _tooltips = {
        'fam_family_entry': _('The family name'),
        'fam_qualifier_combo': _('The family qualifier helps to remove '
                                 'ambiguities that might be associated with '
                                 'this family name'),
        'fam_notes_textview': _('Miscelleanous notes about this family.'),
        'fam_syn_box': _('A list of synonyms for this family.\n\nTo add a '
                         'synonym enter a family name and select one from the '
                         'list of completions.  Then click Add to add it to '\
                         'the list of synonyms.')
     }


    def __init__(self, parent=None):
        super(FamilyEditorView, self).__init__(os.path.join(paths.lib_dir(),
                                                'plugins', 'plants',
                                                'editors.glade'),
                                               parent=parent)
        self.dialog = self.widgets.family_dialog
        self.dialog.set_transient_for(parent)
        self.attach_completion('fam_syn_entry')#, self.syn_cell_data_func)
        self.connect_dialog_close(self.widgets.family_dialog)
        self.restore_state()


    def save_state(self):
        prefs[self.syn_expanded_pref] = \
                                self.widgets.fam_syn_expander.get_expanded()


    def restore_state(self):
        expanded = prefs.get(self.syn_expanded_pref, True)
        self.widgets.fam_syn_expander.set_expanded(expanded)


    def get_window(self):
        '''
        '''
        return self.widgets.family_dialog


    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.fam_ok_button.set_sensitive(sensitive)
        self.widgets.fam_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.fam_next_button.set_sensitive(sensitive)


    def start(self):
        return self.dialog.run()



class FamilyEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'fam_family_entry': 'family',
                           'fam_qualifier_combo': 'qualifier',
                           'fam_notes_textview': 'notes'}

    def __init__(self, model, view):
        '''
        @param model: should be an instance of class Family
        @param view: should be an instance of FamilyEditorView
        '''
        super(FamilyEditorPresenter, self).__init__(model, view)
        self.session = object_session(model)

        # initialize widgets
        self.init_enum_combo('fam_qualifier_combo', 'qualifier')
        self.synonyms_presenter = SynonymsPresenter(self.model, self.view,
                                                    self.session)
        self.refresh_view() # put model values in view

        # connect signals
        self.assign_simple_handler('fam_family_entry', 'family')
        self.assign_simple_handler('fam_qualifier_combo', 'qualifier')
        self.assign_simple_handler('fam_notes_textview', 'notes')

        # for each widget register a signal handler to be notified when the
        # value in the widget changes, that way we can do things like sensitize
        # the ok button
        self.__dirty = False


    def set_model_attr(self, field, value, validator=None):
        #debug('set_model_attr(%s, %s)' % (field, value))
        super(FamilyEditorPresenter, self).set_model_attr(field, value,
                                                          validator)
        self.__dirty = True
        sensitive = self.model.family and True or False
        self.view.set_accept_buttons_sensitive(sensitive)


    def dirty(self):
        return self.__dirty or self.synonyms_presenter.dirty()


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.set_widget_value(widget, value)


    def start(self):
        return self.view.start()


#
# TODO: you shouldn't be able to set a family as a synonym of itself
#
class SynonymsPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_SYNONYM = 1


    def __init__(self, family, view, session):
        '''
        @param model: Family instance
        @param view: see GenericEditorPresenter
        @param session:
        '''
        super(SynonymsPresenter, self).__init__(family, view)
        self.session = session
        self.init_treeview()

        # use completions_model as a dummy object for completions, we'll create
        # seperate SpeciesSynonym models on add
        completions_model = FamilySynonym()
        def fam_get_completions(text):
            query = self.session.query(Family)
            return query.filter(and_(Family.family.like('%s%%' % text),
                                     Family.id != self.model.id))

        self._selected = None
        def on_select(value):
            # don't set anything in the model, just set self._selected
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.fam_syn_add_button.set_sensitive(sensitive)
            self._selected = value
        self.assign_completions_handler('fam_syn_entry', fam_get_completions,
                                        on_select=on_select)


        self.view.widgets.fam_syn_add_button.connect('clicked',
                                                    self.on_add_button_clicked)
        self.view.widgets.fam_syn_remove_button.connect('clicked',
                                                self.on_remove_button_clicked)
        self.__dirty = False


    def dirty(self):
        return self.__dirty


    def init_treeview(self):
        '''
        initialize the gtk.TreeView
        '''
        self.treeview = self.view.widgets.fam_syn_treeview
        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            cell.set_property('text', str(v))
            # just added so change the background color to indicate its new
            if v.id is None:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Synonym', cell)
        col.set_cell_data_func(cell, _syn_data_func)
        self.treeview.append_column(col)

        tree_model = gtk.ListStore(object)
        for syn in self.model._synonyms:
            tree_model.append([syn])
        self.treeview.set_model(tree_model)
        self.treeview.connect('cursor-changed', self.on_tree_cursor_changed)


    def on_tree_cursor_changed(self, tree, data=None):
        '''
        '''
        path, column = tree.get_cursor()
        self.view.widgets.fam_syn_remove_button.set_sensitive(True)


    def refresh_view(self):
        """
        doesn't do anything
        """
        return


    def on_add_button_clicked(self, button, data=None):
        '''
        adds the synonym from the synonym entry to the list of synonyms for
            this species
        '''
        syn = FamilySynonym(family=self.model, synonym=self._selected)
        tree_model = self.treeview.get_model()
        tree_model.append([syn])
        self._selected = None
        entry = self.view.widgets.fam_syn_entry
        self.pause_completions_handler(entry, True)
        entry.set_text('')
        entry.set_position(-1)
        self.pause_completions_handler(entry, False)
        self.view.widgets.fam_syn_add_button.set_sensitive(False)
        self.view.widgets.fam_syn_add_button.set_sensitive(False)
        self.view.set_accept_buttons_sensitive(True)
        self.__dirty = True


    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected synonym from the list of synonyms for
        this species
        '''
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database
        tree = self.view.widgets.fam_syn_treeview
        path, col = tree.get_cursor()
        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]
#        debug('%s: %s' % (value, type(value)))
        s = Family.str(value.synonym)
        msg = 'Are you sure you want to remove %s as a synonym to the ' \
              'current family?\n\n<i>Note: This will not remove the family '\
              '%s from the database.</i>' % (s, s)
        if utils.yes_no_dialog(msg, parent=self.view.get_window()):
            tree_model.remove(tree_model.get_iter(path))
            self.model.synonyms.remove(value.synonym)
            utils.delete_or_expunge(value)
            self.session.flush([value])
            self.view.set_accept_buttons_sensitive(True)
            self.__dirty = True


class FamilyEditor(editor.GenericModelViewPresenterEditor):

    label = 'Family'
    mnemonic_label = '_Family'

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)


    def __init__(self, model=None, parent=None):
        '''
        @param model: Family instance or None
        @param parent: the parent window or None
        '''
        if model is None:
            model = Family()
        super(FamilyEditor, self).__init__(model, parent)

        if parent is None: # should we even allow a change in parent
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []


    def handle_response(self, response):
        '''
        @return: return a list if we want to tell start() to close the editor,
        the list should either be empty or the list of committed values, return
        None if we want to keep editing
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:
                msg = _('Error committing changes.\n\n%s') % \
                      utils.xml_safe_utf8(e.orig)
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the ' \
                      'details for more information.\n\n%s') % \
                      utils.xml_safe_utf8(e)
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = FamilyEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            e = GenusEditor(Genus(family=self.model), self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True


    def start(self):
        self.view = FamilyEditorView(parent=self.parent)
        self.presenter = FamilyEditorPresenter(self.model, self.view)

        # add quick response keys
        dialog = self.view.dialog
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
        self.presenter.cleanup()
        self.session.close() # cleanup session
        return self._committed


#
# Family infobox
#
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
     select_in_search_results
import bauble.paths as paths
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species

class GeneralFamilyExpander(InfoExpander):
    '''
    generic information about an family like number of genus, species,
    accessions and plants
    '''

    def __init__(self, widgets):
        '''
        the constructor
        '''
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.fam_general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box)


    def update(self, row):
        '''
        update the expander

        @param row: the row to get the values from
        '''
        self.set_widget_value('fam_name_data', '<big>%s</big>' % row)
        session = bauble.Session()
        # get the number of genera
        ngen = session.query(Genus).filter_by(family_id=row.id).count()
        self.set_widget_value('fam_ngen_data', ngen)

        # get the number of species
        nsp = session.query(Species).join('genus').\
              filter_by(family_id=row.id).count()
        if nsp == 0:
            self.set_widget_value('fam_nsp_data', 0)
        else:
            ngen_in_sp = session.query(Species.genus_id).\
                join(['genus', 'family']).\
                filter_by(id=row.id).distinct().count()
            self.set_widget_value('fam_nsp_data', '%s in %s genera' \
                                  % (nsp, ngen_in_sp))

        # stop here if no GardenPlugin
        if 'GardenPlugin' not in pluginmgr.plugins:
            return

        # get the number of accessions in the family
        from bauble.plugins.garden.accession import Accession
        from bauble.plugins.garden.plant import Plant

        nacc = session.query(Accession).join(['species', 'genus', 'family']).\
               filter_by(id=row.id).count()
        if nacc == 0:
            self.set_widget_value('fam_nacc_data', nacc)
        else:
            nsp_in_acc = session.query(Accession.species_id).\
                join(['species', 'genus', 'family']).\
                filter_by(id=row.id).distinct().count()
            self.set_widget_value('fam_nacc_data', '%s in %s species' \
                                  % (nacc, nsp_in_acc))

        # get the number of plants in the family
        nplants = session.query(Plant).\
                  join(['accession', 'species', 'genus', 'family']).\
                  filter_by(id=row.id).count()
        if nplants == 0:
            self.set_widget_value('fam_nplants_data', nplants)
        else:
            nacc_in_plants = session.query(Plant.accession_id).\
                join(['accession', 'species', 'genus','family']).\
                filter_by(id=row.id).distinct().count()
            self.set_widget_value('fam_nplants_data', '%s in %s accessions' \
                                  % (nplants, nacc_in_plants))



class SynonymsExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Synonyms"), widgets)
        synonyms_box = self.widgets.fam_synonyms_box
        self.widgets.remove_parent(synonyms_box)
        self.vbox.pack_start(synonyms_box)


    def update(self, row):
        '''
        update the expander

        @param row: the row to get thevalues from
        '''
        #debug(row.synonyms)
        if len(row.synonyms) == 0:
            self.set_sensitive(False)
            self.set_expanded(False)
        else:
            def on_label_clicked(label, event, syn):
                select_in_search_results(syn)
            syn_box = self.widgets.fam_synonyms_box
            for syn in row.synonyms:
                # remove all the children
                syn_box.foreach(syn_box.remove)
                # create clickable label that will select the synonym
                # in the search results
                box = gtk.EventBox()
                label = gtk.Label()
                label.set_alignment(0, .5)
                label.set_markup(Family.str(syn))
                box.add(label)
                utils.make_label_clickable(label, on_label_clicked, syn)
                syn_box.pack_start(box, expand=False, fill=False)
            self.show_all()

            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)



class NotesExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Notes"), widgets)
        notes_box = self.widgets.fam_notes_box
        self.widgets.remove_parent(notes_box)
        self.vbox.pack_start(notes_box)


    def update(self, row):
        if row.notes is None:
            self.set_expanded(False)
            self.set_sensitive(False)
        else:
            self.set_expanded(True)
            self.set_sensitive(True)
            self.set_widget_value('fam_notes_data', row.notes)



class LinksExpander(InfoExpander):

    def __init__(self):
        super(LinksExpander, self).__init__(_('Links'))
        self.tooltips = gtk.Tooltips()
        buttons = []
        self.google_button = gtk.LinkButton("", _("Search Google"))
        self.tooltips.set_tip(self.google_button, _("Search Google"))
        buttons.append(self.google_button)

        self.gbif_button = gtk.LinkButton("", _("Search GBIF"))
        self.tooltips.set_tip(self.gbif_button,
                              _("Search the Global Biodiversity Information "\
                                "Facility"))
        buttons.append(self.gbif_button)

        self.itis_button = gtk.LinkButton("", _("Search ITIS"))
        self.tooltips.set_tip(self.itis_button,
                              _("Search the Intergrated Taxonomic "\
                                "Information System"))
        buttons.append(self.itis_button)

        self.ipni_button = gtk.LinkButton("", _("Search IPNI"))
        self.tooltips.set_tip(self.ipni_button,
                              _("Search the International Plant Names Index"))
        buttons.append(self.ipni_button)

        for b in buttons:
            b.set_alignment(0, -1)
            b.connect("clicked", self.on_click)
            self.vbox.pack_start(b)


    def on_click(self, button):
        desktop.open(button.get_uri())

    def update(self, row):
        s = str(row)
        self.gbif_button.set_uri("http://data.gbif.org/search/%s" % \
                                 s.replace(' ', '+'))
        itis_uri = "http://www.itis.gov/servlet/SingleRpt/SingleRpt?"\
                   "search_topic=Scientific_Name" \
                   "&search_value=%(search_value)s" \
                   "&search_kingdom=Plant" \
                   "&search_span=containing" \
                   "&categories=All&source=html&search_credRating=All" \
                   % {'search_value': s.replace(' ', '%20')}
        self.itis_button.set_uri(itis_uri)

        self.google_button.set_uri("http://www.google.com/search?q=%s" % \
                                   s.replace(' ', '+'))

        ipni_uri = "http://www.ipni.org/ipni/advPlantNameSearch.do?"\
                   "find_family=%s" \
                   "&find_isAPNIRecord=on& find_isGCIRecord=on" \
                   "&find_isIKRecord=on&output_format=normal" % s
        self.ipni_button.set_uri(ipni_uri)



class FamilyInfoBox(InfoBox):
    '''
    '''

    def __init__(self):
        '''
        '''
        InfoBox.__init__(self)
        glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                  'infoboxes.glade')
        self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
        self.general = GeneralFamilyExpander(self.widgets)
        self.add_expander(self.general)
        self.synonyms = SynonymsExpander(self.widgets)
        self.add_expander(self.synonyms)
        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)
        self.links = LinksExpander()
        self.add_expander(self.links)
        self.props = PropertiesExpander()
        self.add_expander(self.props)

        if 'GardenPlugin' not in pluginmgr.plugins:
            self.widgets.remove_parent('fam_nacc_label')
            self.widgets.remove_parent('fam_nacc_data')
            self.widgets.remove_parent('fam_nplants_label')
            self.widgets.remove_parent('fam_nplants_data')


    def update(self, row):
        '''
        '''
        self.general.update(row)
        self.synonyms.update(row)
        self.notes.update(row)
        self.links.update(row)
        self.props.update(row)


__all__ = ['Family', 'FamilyEditor', 'FamilySynonym', 'FamilyInfoBox',
           'family_context_menu', 'family_markup_func']
