#
# Genera table module
#

import os, traceback
import xml

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
from sqlalchemy.ext.associationproxy import association_proxy

import bauble
from bauble.i18n import _
from bauble.editor import *
import bauble.utils as utils
import bauble.utils.sql as sql_utils
import bauble.utils.desktop as desktop
from bauble.types import Enum
from bauble.utils.log import debug
import bauble.paths as paths
from bauble.view import InfoBox, InfoExpander, PropertiesExpander, \
     select_in_search_results

# TODO: warn the user that a duplicate genus name is being entered
# even if only the author or qualifier is different

# TODO: should be a higher_taxon column that holds values into
# subgen, subfam, tribes etc, maybe this should be included in Genus

# TODO: since there can be more than one genus with the same name but
# different authors we need to show the Genus author in the result search
# and at least give the Genus it's own infobox, we should also check if
# when entering a plantname with a chosen genus if that genus has an author
# ask the user if they want to use the accepted name and show the author of
# the genus then so they aren't using the wrong version of the Genus,
# e.g. Cananga

def edit_callback(value):
    session = bauble.Session()
    e = GenusEditor(model=session.merge(value))
    return e.start() != None


def add_species_callback(value):
    from bauble.plugins.plants.species_editor import SpeciesEditor
    session = bauble.Session()
    e = SpeciesEditor(model=Species(genus=session.merge(value)))
    return e.start() != None


def remove_callback(value):
    # TODO: before removing we should get the object, find all the dependent
    # objects for the class and then find all the child objects that refer
    # to the object to be removed and at least say something like,
    # '522 species refer to this object, do you still want to remove it'
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = _("Are you sure you want to remove %s?") % utils.xml_safe_utf8(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = bauble.Session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True


genus_context_menu = [(_('Edit'), edit_callback),
                      ('--', None),
                      (_('Add species'), add_species_callback),
                      ('--', None),
                      (_('Remove'), remove_callback)]


def genus_markup_func(genus):
    '''
    '''
    return str(genus), str(genus.family)



class Genus(bauble.Base, bauble.Table):
    """
    Table: genus

    Columns
    -------

    genus: The name of the genus. The genus is not unique since we can
    have two genera with the same name but different authors.

    hybrid: indicates whether the name in the Genus Name field refers to an
      Intergeneric hybrid or an Intergeneric graft chimaera.
      Content of genhyb   Nature of Name in gen
      H        An intergeneric hybrid collective name
      x        An Intergeneric Hybrid
      +        An Intergeneric Graft Hybrid or Graft Chimaera

    qualifier: designates the botanical status of the genus.
      Possible values:
        s. lat. - aggregrate family (sensu lato)
        s. str. - segregate family (sensu stricto)


    Contraints
    ----------
    """
    __tablename__ = 'genus'
    __table_args__ = (UniqueConstraint('genus', 'hybrid', 'author',
                                       'qualifier', 'family_id'),
                      {})
    __mapper_args__ = {'order_by': ['genus', 'author']}

    # columns
    id = Column(Integer, primary_key=True)
    genus = Column(String(64), nullable=False, index=True)
    hybrid = Column(Enum(values=['H', 'x', '+', '']), default=u'')
    author = Column(Unicode(255), default=u'')
    qualifier = Column(Enum(values=['s. lat.', 's. str', '']), default=u'')
    notes = Column(UnicodeText)
    family_id = Column(Integer, ForeignKey('family.id'), nullable=False)

    # relations
    synonyms = association_proxy('_synonyms', 'synonym')
    _synonyms = relation('GenusSynonym',
                         primaryjoin='Genus.id==GenusSynonym.genus_id',
                         cascade='all, delete-orphan', uselist=True,
                         backref='genus')

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this genus
    # get deleted if this genus gets deleted
    __syn = relation('GenusSynonym',
                     primaryjoin='Genus.id==GenusSynonym.synonym_id',
                     cascade='all, delete-orphan', uselist=True)


    def __str__(self):
        return Genus.str(self)


    @staticmethod
    def str(genus, author=False):
        if genus.genus is None:
            return repr(genus)
        elif not author or genus.author is None:
            return ' '.join([s for s in [genus.hybrid, genus.genus,
                                    genus.qualifier] if s not in ('', None)])
        else:
            return ' '.join(
                [s for s in [genus.hybrid, genus.genus,
                genus.qualifier,
                xml.sax.saxutils.escape(genus.author)] if s not in ('', None)])


class GenusSynonym(bauble.Base, bauble.Table):
    __tablename__ = 'genus_synonym'
    __table_args__ = (UniqueConstraint('genus_id', 'synonym_id',
                                        name='genus_synonym_index'),
                      {})
    # columns
    id = Column(Integer, Sequence('genus_id_seq'), primary_key=True)
    genus_id = Column(Integer, ForeignKey('genus.id'), nullable=False)
    synonym_id = Column(Integer, ForeignKey('genus.id'), nullable=False)

    # relations
    synonym = relation('Genus', uselist=False,
                       primaryjoin='GenusSynonym.synonym_id==Genus.id')

    def __init__(self, synonym=None, **kwargs):
        # it is necessary that the first argument here be synonym for
        # the Genus.synonyms association_proxy to work
        self.synonym = synonym
        super(GenusSynonym, self).__init__(**kwargs)

    def __str__(self):
        return str(self.synonym)

# genus_table = \
#     bauble.Table('genus', bauble.metadata,
#                  Column('id', Integer, primary_key=True),
#                  # it is possible that there can be genera with the same
#                  # name but different authors and probably means that at
#                  # different points in literature this name was used but
#                  # is now a synonym even though it may not be a synonym
#                  # for the same species, this screws us up b/c you can
#                  # now enter duplicate genera, somehow
#                  # NOTE: we should at least warn the user that a duplicate
#                  # is being entered
#                  Column('genus', String(64), nullable=False, index=True),
#                  Column('hybrid', Enum(values=['H', 'x', '+', None],
#                                           empty_to_none=True)),
#                  Column('author', Unicode(255)),
#                  Column('qualifier',Enum(values=['s. lat.', 's. str', None],
#                                          empty_to_none=True)),
#                  Column('notes', UnicodeText),
#                  Column('family_id', Integer, ForeignKey('family.id'),
#                         nullable=False),
#                  UniqueConstraint('genus', 'hybrid', 'author', 'family_id',
#                                   name='genus_index'))



# class Genus(bauble.BaubleMapper):

#     synonyms = association_proxy('_synonyms', 'synonym')

#     def __str__(self):
#         return Genus.str(self)


#     @staticmethod
#     def str(genus, author=False):
#         if genus.genus is None:
#             return repr(genus)
#         elif not author or genus.author is None:
#             return ' '.join([s for s in [genus.hybrid, genus.genus,
#                                          genus.qualifier] if s is not None])
#         else:
#             return ' '.join(
#                 [s for s in [genus.hybrid, genus.genus,
#                 genus.qualifier,
#                 xml.sax.saxutils.escape(genus.author)] if s is not None])


# genus_synonym_table = bauble.Table('genus_synonym', bauble.metadata,
#                             Column('id', Integer, primary_key=True),
#                             Column('genus_id', Integer, ForeignKey('genus.id'),
#                                    nullable=False),
#                             Column('synonym_id', Integer,
#                                    ForeignKey('genus.id'), nullable=False),
#                             UniqueConstraint('genus_id', 'synonym_id',
#                                              name='genus_synonym_index'))


# class GenusSynonym(bauble.BaubleMapper):


#     def __init__(self, genus=None):
#         """
#         @param genus: a Genus object that will be used as the synonym
#         """
#         self.synonym = genus


#     def __str__(self):
#         return str(self.synonym)


# late bindings
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.species_model import Species
from bauble.plugins.plants.species_editor import SpeciesEditor
Genus.species = relation('Species', cascade='all, delete-orphan',
                         order_by=['sp', 'infrasp_rank', 'infrasp'],
                         backref=backref('genus', uselist=False))
# Genus._synonyms = relation('GenusSynonym',
#                            primaryjoin=Genus.id==GenusSynonym.genus_id,
#                            cascade='all, delete-orphan', uselist=True,
#                            backref='genus')#, order_by=['genus', 'author'])
#GenusSynonym.synonym = relation('Genus', uselist=False,
#                                primaryjoin=GenusSynonym.synonym_id==Genus.id)

# mapper(Genus, genus_table,
#     properties = {\
#     'species': relation(Species, cascade='all, delete-orphan',
#                         order_by=['sp', 'infrasp_rank', 'infrasp'],
#                         backref=backref('genus', uselist=False)),
#     '_synonyms': relation(GenusSynonym,
#                 primaryjoin=genus_table.c.id==genus_synonym_table.c.genus_id,
#                 cascade='all, delete-orphan', uselist=True,
#                 backref='genus')},
#     order_by=['genus', 'author'])

# mapper(GenusSynonym, genus_synonym_table,
#     properties = {\
#     'synonym': relation(Genus, uselist=False,
#             primaryjoin=genus_synonym_table.c.synonym_id==genus_table.c.id)})


class GenusEditorView(GenericEditorView):

    syn_expanded_pref = 'editor.genus.synonyms.expanded'
    expanders_pref_map = {'gen_syn_expander': 'editor.genus.synonyms.expanded',
                          'gen_notes_expander': 'editor.genus.notes.expanded'}

    _tooltips = {
        'gen_family_entry': _('The family name'),
        'gen_hybrid_combo': _('The type of hybrid for this genus.'),
        'gen_genus_entry': _('The genus name'),
        'gen_author_entry': _('The name or abbreviation of the author that '\
                              'published this genus'),
        'gen_syn_box': _('A list of synonyms for this genus.\n\nTo add a '
                         'synonym enter a family name and select one from the '
                         'list of completions.  Then click Add to add it to '\
                         'the list of synonyms.'),
        'gen_notes_textview': _('Miscelleanous notes about this genus.')
     }


    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(),
                                                      'plugins', 'plants',
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.genus_dialog
        self.dialog.set_transient_for(parent)
        self.connect_dialog_close(self.dialog)
        self.attach_completion('gen_syn_entry', self.syn_cell_data_func)
        self.attach_completion('gen_family_entry')
        self.restore_state()


    def syn_cell_data_func(self, column, renderer, model, iter, data=None):
        '''
        '''
        v = model[iter][0]
        author = None
        if v.author is None:
            author = ''
        else:
            author = utils.xml_safe(unicode(v.author))
        renderer.set_property('markup', '<i>%s</i> %s (<small>%s</small>)' \
                              % (Genus.str(v), author, Family.str(v.family)))


    def save_state(self):
        '''
        save the current state of the gui to the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            prefs[pref] = self.widgets[expander].get_expanded()


    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            expanded = prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)


    def _get_window(self):
        '''
        '''
        return self.widgets.family_dialog
    window = property(_get_window)


    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.gen_ok_button.set_sensitive(sensitive)
        self.widgets.gen_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.gen_next_button.set_sensitive(sensitive)


    def start(self):
        return self.dialog.run()


class GenusEditorPresenter(GenericEditorPresenter):

    widget_to_field_map = {'gen_family_entry': 'family',
                           'gen_genus_entry': 'genus',
                           'gen_author_entry': 'author',
                           'gen_hybrid_combo': 'hybrid',
#                           'gen_qualifier_combo': 'qualifier'
                           'gen_notes_textview': 'notes'}


    def __init__(self, model, view):
        '''
        @model: should be an instance of class Genus
        @view: should be an instance of GenusEditorView
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(model), view)
        self.session = object_session(model)

        # initialize widgets
        self.init_enum_combo('gen_hybrid_combo', 'hybrid')
        self.synonyms_presenter = SynonymsPresenter(self.model, self.view,
                                                    self.session)
        self.refresh_view() # put model values in view

        # connect signals
        def fam_get_completions(text):
            query = self.session.query(Family)
            return query.filter(Family.c.family.like('%s%%' % text))

        def set_in_model(self, field, value):
            setattr(self.model, field, value)

        self.assign_completions_handler('gen_family_entry', 'family',
                                        fam_get_completions,
                                        set_func=set_in_model)
        self.assign_simple_handler('gen_genus_entry', 'genus')
        self.assign_simple_handler('gen_hybrid_combo', 'hybrid',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('gen_author_entry', 'author',
                                   UnicodeOrNoneValidator())
        #self.assign_simple_handler('gen_qualifier_combo', 'qualifier')
        self.assign_simple_handler('gen_notes_textview', 'notes',
                                   UnicodeOrNoneValidator())

        # for each widget register a signal handler to be notified when the
        # value in the widget changes, that way we can do things like sensitize
        # the ok button
        for field in self.widget_to_field_map.values():
            self.model.add_notifier(field, self.on_field_changed)


    def on_field_changed(self, model, field):
        sensitive = False
        if self.model.family and self.model.genus:
            sensitive = True
        self.view.set_accept_buttons_sensitive(sensitive)


    def dirty(self):
        return self.model.dirty or self.synonyms_presenter.dirty()


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            if field == 'family_id':
                value = self.model.family
            else:
                value = self.model[field]
            self.view.set_widget_value(widget, value)


    def start(self):
        return self.view.start()


#
# TODO: you shouldn't be able to set a genus as a synonym of itself
#
class SynonymsPresenter(GenericEditorPresenter):

    PROBLEM_INVALID_SYNONYM = 1


    def __init__(self, genus, view, session):
        '''
        @param model: Genus instance
        @param view: see GenericEditorPresenter
        @param session:
        '''
        GenericEditorPresenter.__init__(self, ModelDecorator(genus), view)
        self.session = session
        self.init_treeview()

        # use completions_model as a dummy object for completions, we'll create
        # seperate SpeciesSynonym models on add
        completions_model = GenusSynonym()
        def gen_get_completions(text):
            query = self.session.query(Genus)
            query = query.filter(and_(genus_table.c.genus.like('%s%%' % text),
                                      genus_table.c.id != self.model.id))
            return query

        def set_in_model(self, field, value):
            # don't set anything in the model, just set self.selected
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.gen_syn_add_button.set_sensitive(sensitive)
            self._added = value

        self.assign_completions_handler('gen_syn_entry', 'synonym',
                                        gen_get_completions,
                                        set_func=set_in_model,
                                        model=completions_model)

        self._added = None
        self.view.widgets.gen_syn_add_button.connect('clicked',
                                                    self.on_add_button_clicked)
        self.view.widgets.gen_syn_remove_button.connect('clicked',
                                                self.on_remove_button_clicked)
        self.__dirty = False


    def start(self):
        raise Exception('genus.SynonymsPresenter cannot be started')


    def dirty(self):
        return self.model.dirty or self.__dirty


    def init_treeview(self):
        '''
        initialize the gtk.TreeView
        '''
        self.treeview = self.view.widgets.gen_syn_treeview
        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            syn = v.synonym
            cell.set_property('markup', '<i>%s</i> %s (<small>%s</small>)' \
                              % (Genus.str(syn),
                                 utils.xml_safe(unicode(syn.author)),
                                 Family.str(syn.family)))
            # set background color to indicate its new
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
        self.view.widgets.gen_syn_remove_button.set_sensitive(True)


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
        syn = GenusSynonym(self._added)
        self.model._synonyms.append(syn)
        tree_model = self.treeview.get_model()
        tree_model.append([syn])
        self._added = None
        entry = self.view.widgets.gen_syn_entry
        # sid generated from GenericEditorPresenter.assign_completion_handler
        entry.handler_block(self._insert_gen_syn_entry_sid)
        entry.set_text('')
        entry.set_position(-1)
        entry.handler_unblock(self._insert_gen_syn_entry_sid)
        self.view.widgets.gen_syn_add_button.set_sensitive(False)
        self.view.widgets.gen_syn_add_button.set_sensitive(False)
        self.view.set_accept_buttons_sensitive(True)
        self.__dirty = True


    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected synonym from the list of synonyms for
        this species
        '''
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database
        tree = self.view.widgets.gen_syn_treeview
        path, col = tree.get_cursor()
        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]
        s = Genus.str(value.synonym)
        msg = _('Are you sure you want to remove %(genus)s as a synonym to '
                'the current genus?\n\n<i>Note: This will not remove the '
                'genus from the database.</i>') % {'genus': s}
        if utils.yes_no_dialog(msg, parent=self.view.window):
            tree_model.remove(tree_model.get_iter(path))
            self.model._synonyms.remove(value)
            utils.delete_or_expunge(value)
            self.session.flush([value])
            self.view.set_accept_buttons_sensitive(True)
            self.__dirty = True


class GenusEditor(GenericModelViewPresenterEditor):

    label = 'Genus'
    mnemonic_label = '_Genus'

    # these response values have to correspond to the response values in
    # the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)


    def __init__(self, model=None, parent=None):
        '''
        @param model: Genus instance or None
        @param parent: None
        '''
        # the view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        if model is None:
            model = Genus()
        GenericModelViewPresenterEditor.__init__(self, model, parent)

        if parent is None: # should we even allow a change in parent
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []


    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = _('Are you sure you want to lose your changes?')
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
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') % \
                        utils.xml_safe_utf8(e)
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.dirty() \
                 and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            model = Genus(family=self.model.family)
            e = GenusEditor(model=model, parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            sp = Species(genus=self.model)
            e = SpeciesEditor(model=sp, parent=self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True


    def start(self):
        if self.session.query(Family).count() == 0:
            msg = _('You must first add or import at least one Family into '\
                    'the database before you can add plants.')
            utils.message_dialog(msg)
            return
        self.view = GenusEditorView(parent=self.parent)
        self.presenter = GenusEditorPresenter(self.model, self.view)

        # add quick response keys
        dialog = self.view.dialog
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set default focus
        if self.model.family is None:
            self.view.widgets.gen_family_entry.grab_focus()
        else:
            self.view.widgets.gen_genus_entry.grab_focus()

        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break
        self.session.close() # cleanup session
        return self._committed


from bauble.plugins.plants.species_model import Species#, species_table

# TODO: need to reenable imports
#from bauble.plugins.garden.accession import Accession, accession_table
#from bauble.plugins.garden.plant import Plant, plant_table

#
# Infobox and InfoExpanders
#

class LinksExpander(InfoExpander):

    """
    A collection of link buttons to use for internet searches.
    """

    def __init__(self):
        InfoExpander.__init__(self, _("Links"))
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

        self.bgci_button = gtk.LinkButton("", _("Search BGCI"))
        self.tooltips.set_tip(self.bgci_button,
                              _("Search Botanic Gardens Conservation " \
                                "International"))
        buttons.append(self.bgci_button)

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

        bgci_uri = "http://www.bgci.org/plant_search.php?action=Find"\
                   "&ftrGenus=%s&ftrRedList="\
                   "&ftrRedList1997=&ftrEpithet=&ftrCWR=&x=0&y=0#results" % s
        self.bgci_button.set_uri(bgci_uri)

        ipni_uri = "http://www.ipni.org/ipni/advPlantNameSearch.do?"\
                   "find_genus=%s&find_isAPNIRecord=on& find_isGCIRecord=on" \
                   "&find_isIKRecord=on&output_format=normal" % s
        self.ipni_button.set_uri(ipni_uri)


class GeneralGenusExpander(InfoExpander):
    '''
    expander to present general information about a genus
    '''

    def __init__(self, widgets):
        '''
        the constructor
        '''
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.gen_general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box)

        self.current_obj = None
        def on_family_clicked(*args):
            select_in_search_results(self.current_obj.family)
        utils.make_label_clickable(self.widgets.gen_fam_data,
                                   on_family_clicked)


    def update(self, row):
        '''
        update the expander

        @param row: the row to get the values from
        '''
        self.current_obj = row
        self.set_widget_value('gen_name_data', '<big>%s</big> %s' % \
                                  (row, utils.xml_safe(unicode(row.author))))
        self.set_widget_value('gen_fam_data',
                              (utils.xml_safe(unicode(row.family))))
        # get the number of species
        species_ids = select([species_table.c.id],
                             species_table.c.genus_id==row.id)
        nsp = sql_utils.count_select(species_ids)
        self.set_widget_value('gen_nsp_data', nsp)

        # get number of accessions
        acc_ids = select([accession_table.c.id],
                         accession_table.c.species_id.in_(species_ids))
        nacc_str = str(sql_utils.count_select(acc_ids))
        if nacc_str != '0':
            nsp_with_accessions = sql_utils.count_distinct_whereclause(accession_table.c.species_id, accession_table.c.species_id.in_(species_ids))
            nacc_str = '%s in %s species' % (nacc_str, nsp_with_accessions)
        self.set_widget_value('gen_nacc_data', nacc_str)

        # get number of plants
        plant_ids = select([plant_table.c.id], plant_table.c.accession_id.in_(acc_ids))
        nplants_str = str(sql_utils.count_select(plant_ids))
        if nplants_str != '0':
            nacc_with_plants = sql_utils.count_distinct_whereclause(plant_table.c.accession_id, plant_table.c.accession_id.in_(acc_ids))
            nplants_str = '%s in %s accessions' % (nplants_str,
                                                   nacc_with_plants)
        self.set_widget_value('gen_nplants_data', nplants_str)



class SynonymsExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Synonyms"), widgets)
        synonyms_box = self.widgets.gen_synonyms_box
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
            syn_box = self.widgets.gen_synonyms_box
            for syn in row.synonyms:
                # remove all the children
                syn_box.foreach(syn_box.remove)
                # create clickable label that will select the synonym
                # in the search results
                box = gtk.EventBox()
                label = gtk.Label()
                label.set_alignment(0, .5)
                label.set_markup(Genus.str(syn, author=True))
                box.add(label)
                utils.make_label_clickable(label, on_label_clicked, syn)
                syn_box.pack_start(box, expand=False, fill=False)

            self.set_sensitive(True)
            # TODO: get expanded state from prefs
            self.set_expanded(True)



class NotesExpander(InfoExpander):

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Notes"), widgets)
        notes_box = self.widgets.gen_notes_box
        self.widgets.remove_parent(notes_box)
        self.vbox.pack_start(notes_box)


    def update(self, row):
        if row.notes is None:
            self.set_expanded(False)
            self.set_sensitive(False)
        else:
            self.set_expanded(True)
            self.set_sensitive(True)
            self.set_widget_value('gen_notes_data', row.notes)



class GenusInfoBox(InfoBox):
    """
    - number of taxon in number of accessions
    - references
    """
    def __init__(self):
        InfoBox.__init__(self)
        glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                  'infoboxes.glade')
        self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
        self.general = GeneralGenusExpander(self.widgets)
        self.add_expander(self.general)
        self.synonyms = SynonymsExpander(self.widgets)
        self.add_expander(self.synonyms)
        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)
        self.links = LinksExpander()
        self.add_expander(self.links)
        self.props = PropertiesExpander()
        self.add_expander(self.props)


    def update(self, row):
        self.general.update(row)
        self.synonyms.update(row)
        self.notes.update(row)
        self.links.update(row)
        self.props.update(row)



__all__ = ['Genus', 'GenusSynonym', 'GenusEditor', 'GenusInfoBox',
           'genus_context_menu', 'genus_markup_func']
