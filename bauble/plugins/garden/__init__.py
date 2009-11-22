#
# garden plugin
#

import os, sys
import bauble
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
from bauble.view import SearchView
from bauble.plugins.garden.accession import *
from bauble.plugins.garden.location import *
from bauble.plugins.garden.plant import *
from bauble.plugins.garden.source import *
from bauble.plugins.garden.donor import *
from bauble.plugins.garden.institution import *
from bauble.plugins.garden.propagation import *
from bauble.utils.log import debug

# other ideas:
# - cultivation table
# - conservation table

def natsort_kids(kids):
    return lambda(parent): sorted(getattr(parent, kids),key=utils.natsort_key)


class GardenPlugin(pluginmgr.Plugin):

    depends = ["PlantsPlugin"]
    tools = [InstitutionTool]
    commands = [InstitutionCommand]

    @classmethod
    def install(cls, *args, **kwargs):
        pass

    @classmethod
    def init(cls):
        from bauble.plugins.plants import Species
        mapper_search = SearchView.get_search_strategy('MapperSearch')

        mapper_search.add_meta(('accession', 'acc'), Accession, ['code'])
        SearchView.view_meta[Accession].set(children=natsort_kids("plants"),
                                            infobox=AccessionInfoBox,
                                            context_menu=acc_context_menu,
                                            markup_func=acc_markup_func)

        mapper_search.add_meta(('location', 'loc'), Location, ['name'])
        SearchView.view_meta[Location].set(children=natsort_kids('plants'),
                                           infobox=LocationInfoBox,
                                           context_menu=loc_context_menu,
                                           markup_func=loc_markup_func)

        mapper_search.add_meta(('plant', 'plants'), Plant, ['code'])
        SearchView.add_search_strategy(PlantSearch)
        SearchView.view_meta[Plant].set(infobox=PlantInfoBox,
                                        context_menu=plant_context_menu,
                                        markup_func=plant_markup_func)

        mapper_search.add_meta(('donor', 'don'), Donor, ['name'])
        SearchView.view_meta[Donor].set(children=natsort_kids('donations'),
                                        infobox=DonorInfoBox,
                                        context_menu=donor_context_menu)

        mapper_search.add_meta(('collection', 'col', 'coll'),
                               Collection, ['locale'])
        source_kids = lambda src: sorted(src.accession.plants,
                                       key=utils.natsort_key)
        SearchView.view_meta[Collection].set(children=source_kids,
                                             infobox=SourceInfoBox,
                                             markup_func=source_markup_func,
                                             context_menu=source_context_menu)

        SearchView.view_meta[Donation].set(children=source_kids,
                                           infobox=SourceInfoBox,
                                           markup_func=source_markup_func,
                                           context_menu=source_context_menu)


        # done here b/c the Species table is not part of this plugin
        SearchView.view_meta[Species].child = "accessions"

        if bauble.gui is not None:
            bauble.gui.add_to_insert_menu(AccessionEditor, _('Accession'))
            bauble.gui.add_to_insert_menu(PlantEditor, _('Plant'))
            bauble.gui.add_to_insert_menu(LocationEditor, _('Location'))
            #bauble.gui.add_to_insert_menu(DonorEditor, _('Donor'))

        # if the plant delimiter isn't in the bauble meta then add the default
        import bauble.meta as meta
        meta.get_default(plant_delimiter_key, default_plant_delimiter)


def init_location_comboentry(presenter, combo, on_select):
    """
    The plant_loc_comboentry requires more custom setup than
    view.attach_completion and self.assign_simple_handler can
    provides.  This method allows us to have completions on the
    location entry based on the location code, location name and
    location string as well as selecting a location from a combo
    drop down.

    :param presenter:
    :param combo:
    :param on_select:
    """
    PROBLEM = 'unknown_location'

    def cell_data_func(col, cell, model, treeiter, data=None):
        cell.props.text = utils.utf8(model[treeiter][0])

    completion = gtk.EntryCompletion()
    cell = gtk.CellRendererText() # set up the completion renderer
    completion.pack_start(cell)
    completion.set_cell_data_func(cell, cell_data_func)

    entry = combo.child
    entry.set_completion(completion)

    combo.clear()
    cell = gtk.CellRendererText()
    combo.pack_start(cell)
    combo.set_cell_data_func(cell, cell_data_func)

    model = gtk.ListStore(object)
    for location in presenter.session.query(Location):
        model.append([location])
    combo.set_model(model)
    completion.set_model(model)

    def on_match_select(completion, model, treeiter):
        value = model[treeiter][0]
        on_select(value)
        presenter.remove_problem(PROBLEM, entry)
        presenter.refresh_sensitivity()
        return True
    presenter.view.connect(completion, 'match-selected', on_match_select)

    def on_entry_changed(entry, presenter):
        text = utils.utf8(entry.props.text)
        # see if the text matches a completion string
        comp = entry.get_completion()
        compl_model = comp.get_model()
        def _cmp(row, data):
            return utils.utf8(row[0]) == data
        found = utils.search_tree_model(compl_model, text, _cmp)
        if len(found) == 1:
            comp.emit('match-selected', compl_model, found[0])
            return True
        # see if the text matches exactly a code or name
        codes = presenter.session.query(Location).filter(Location.code==text)
        names = presenter.session.query(Location).filter(Location.name==text)
        # TODO: why the hell do we get an error here when we run all
        # the PlantTests but not the specific test_editor_transfer
        if codes.count() == 1:
            location = codes.first()
            presenter.remove_problem(PROBLEM, entry)
            on_select(location)
        elif names.count() == 1:
            location = names.first()
            presenter.remove_problem(PROBLEM, entry)
            on_select(location)
        else:
            presenter.add_problem(PROBLEM, entry)
        return True
    presenter.view.connect(entry, 'changed', on_entry_changed, presenter)

    def on_combo_changed(combo, *args):
        model = combo.get_model()
        i = combo.get_active_iter()
        if not i:
            return
        location = combo.get_model()[i][0]
        combo.child.props.text = str(location)
    presenter.view.connect(combo, 'changed', on_combo_changed)


plugin = GardenPlugin
