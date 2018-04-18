# -*- coding: utf-8 -*-
#
# Copyright 2015 Mario Frasca <mario@anche.no>.
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

import os
import gtk

import logging
logger = logging.getLogger(__name__)


from bauble import utils
from bauble import db
from bauble.plugins.plants import (Familia, Genus, Species, VernacularName, SpeciesNote)
from bauble.plugins.garden.plant import (Plant, PlantNote)
from bauble.plugins.garden.accession import (Accession, AccessionNote)
from bauble.plugins.garden.source import (Source, Contact)
from bauble.plugins.garden.location import (Location)
import bauble.task
from bauble import editor
from bauble import paths
import json
from bauble import pluginmgr
from bauble import pb_set_fraction


def serializedatetime(obj):
    """Default JSON serializer."""
    import calendar
    import datetime

    if isinstance(obj, (Familia, Genus, Species)):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = calendar.timegm(obj.timetuple()) * 1000
    try:
        millis += int(obj.microsecond / 1000)
    except AttributeError:
        pass
    return {'__class__': 'datetime', 'millis': millis}


class JSONExporter(editor.GenericEditorPresenter):
    '''Export taxonomy and plants in JSON format.

    the Presenter ((M)VP)'''

    last_folder = ''
    widget_to_field_map = {
        'sbo_selection': 'selection_based_on',
        'sbo_taxa': 'selection_based_on',
        'sbo_accessions': 'selection_based_on',
        'sbo_plants': 'selection_based_on',
        'ei_referred': 'export_includes',
        'ei_referring': 'export_includes',
        'chkincludeprivate': 'include_private',
        'filename': 'filename',
        }

    view_accept_buttons = ['sed-button-ok', 'sed-button-cancel', ]

    def __init__(self, view):
        self.selection_based_on = 'sbo_selection'
        self.export_includes = 'ei_referred'
        self.include_private = True
        self.filename = ''
        super(JSONExporter, self).__init__(
            model=self, view=view, refresh_view=True)

    def get_objects(self):
        '''return the list of objects to be exported

        if "based_on" is "selection", return the top level selection only.

        if "based_on" is something else, return all that is needed to create
        a complete export.
        '''
        if self.selection_based_on == 'sbo_selection':
            if self.include_private:
                logger.info('exporting selection overrides `include_private`')
            result = self.view.get_selection()
            if result is None:
                return result
            vernacular = speciesnotes = plantnotes = accessionnotes = []
            species = [j.id for j in result if isinstance(j, Species)]
            if species:
                vernacular = self.session.query(VernacularName).filter(
                    VernacularName.species_id.in_(species)).all()
                speciesnotes = self.session.query(SpeciesNote).filter(
                    SpeciesNote.species_id.in_(species)).all()
            plants = [j.id for j in result if isinstance(j, Plant)]
            if plants:
                plantnotes = self.session.query(PlantNote).filter(
                    PlantNote.plant_id.in_(plants)).all()
            accessions = [j.id for j in result if isinstance(j, Accession)]
            if accessions:
                accessionnotes = self.session.query(AccessionNote).filter(
                    AccessionNote.accession_id.in_(accessions)).all()
            return result + vernacular + plantnotes + accessionnotes + speciesnotes

        ## export disregarding selection
        result = []
        if self.selection_based_on == 'sbo_plants':
            plant_query = self.session.query(
                Plant).order_by(Plant.code).join(
                Accession).order_by(Accession.code)
            if self.include_private is False:
                plant_query = plant_query.filter(
                    Accession.private == False)  # `is` does not work
            plants = plant_query.all()
            plantnotes = self.session.query(PlantNote).filter(
                PlantNote.plant_id.in_([j.id for j in plants])).all()
            ## only used locations and accessions
            locations = self.session.query(Location).filter(
                Location.id.in_([j.location_id for j in plants])).all()
            accessions = self.session.query(Accession).filter(
                Accession.id.in_([j.accession_id for j in plants])).order_by(
                Accession.code).all()
            ## notes are linked in opposite direction
            accessionnotes = self.session.query(AccessionNote).filter(
                AccessionNote.accession_id.in_(
                    [j.id for j in accessions])).all()
            ## all used contacts, but please don't repeat them.
            contacts = list(set(a.source.source_detail for a in accessions if a.source))
            # extend results with things not further used
            result.extend(locations)
            result.extend(plants)
            result.extend(plantnotes)
        elif self.selection_based_on == 'sbo_accessions':
            accessions = self.session.query(Accession).order_by(
                Accession.code).all()
            if self.include_private is False:
                accessions = [j for j in accessions if j.private is False]
            accessionnotes = self.session.query(AccessionNote).filter(
                AccessionNote.accession_id.in_(
                    [j.id for j in accessions])).all()
            ## all used contacts, but please don't repeat them.
            contacts = list(set(a.source.source_detail for a in accessions if a.source))
        else:
            contacts = []

        ## now the taxonomy, based either on all species or on the ones used
        if self.selection_based_on == 'sbo_taxa':
            species = self.session.query(Species).order_by(
                Species.sp).all()
        else:
            # prepend results with accession data
            result = accessions + accessionnotes + result

            species = self.session.query(Species).filter(
                Species.id.in_([j.species_id for j in accessions])).order_by(
                Species.sp).all()

        vernacular = self.session.query(VernacularName).filter(
            VernacularName.species_id.in_([j.id for j in species])).all()

        ## and all used genera and families
        genera = self.session.query(Genus).filter(
            Genus.id.in_([j.genus_id for j in species])).order_by(
            Genus.genus).all()
        families = self.session.query(Familia).filter(
            Familia.id.in_([j.family_id for j in genera])).order_by(
            Familia.family).all()

        # this should really be generalized, but while in 1.0 there's no point.
        speciesnotes = self.session.query(SpeciesNote).filter(
            SpeciesNote.species_id.in_(
                [j.id for j in species])).all()

        ## prepend the result with the taxonomic information
        result = families + genera + species + speciesnotes + vernacular + contacts + result
        print vernacular
        print speciesnotes

        ## done, return the result
        return result

    def on_btnbrowse_clicked(self, button):
        self.view.run_file_chooser_dialog(
            _("Choose a file…"), None,
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                     gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
            last_folder=self.last_folder, target='filename')
        filename = self.view.widget_get_value('filename')
        JSONExporter.last_folder, bn = os.path.split(filename)

    def on_btnok_clicked(self, widget):
        self.run()  # should go in the background really

    def on_btncancel_clicked(self, widget):
        pass

    def run(self):
        "perform the export"

        filename = self.filename
        if os.path.exists(filename) and not os.path.isfile(filename):
            raise ValueError("%s exists and is not a a regular file"
                             % filename)

        objects = self.get_objects()
        # if objects is None then export all objects under classes Familia,
        # Genus, Species, Accession, Plant, Location.
        if objects is None:
            s = db.Session()
            objects = s.query(Familia).all()
            objects.extend(s.query(Genus).all())
            objects.extend(s.query(Species).all())
            objects.extend(s.query(VernacularName).all())
            objects.extend(s.query(Accession).all())
            objects.extend(s.query(Plant).all())
            objects.extend(s.query(Location).all())

        count = len(objects)
        if count > 3000:
            msg = _('You are exporting %(nplants)s objects to JSON format.  '
                    'Exporting this many objects may take several minutes.  '
                    '\n\n<i>Would you like to continue?</i>') \
                % ({'nplants': count})
            if not self.view.run_yes_no_dialog(msg):
                return

        import codecs
        with codecs.open(filename, "wb", "utf-8") as output:
            output.write('[')
            output.write(',\n '.join(
                [json.dumps(obj.as_dict(),
                            default=serializedatetime, sort_keys=True)
                 for obj in objects]))
            output.write(']')


class JSONImporter(editor.GenericEditorPresenter):
    '''The import process will be queued as a bauble task. there is no callback
    informing whether it is successfully completed or not.

    the Presenter ((M)VP)
    Model (attributes container) is the Presenter itself.
    '''

    widget_to_field_map = {'chk_create': 'create',
                           'chk_update': 'update',
                           'input_filename': 'filename',
                           }
    last_folder = ''

    view_accept_buttons = ['sid-button-ok', 'sid-button-cancel', ]

    def __init__(self, view):
        self.filename = ''
        self.update = True
        self.create = True
        super(JSONImporter, self).__init__(
            model=self, view=view, refresh_view=True)
        self.__error = False   # flag to indicate error on import
        self.__cancel = False  # flag to cancel importing
        self.__pause = False   # flag to pause importing
        self.__error_exc = False

    def on_btnbrowse_clicked(self, button):
        self.view.run_file_chooser_dialog(
            _("Choose a file…"), None,
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                     gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL),
            last_folder=self.last_folder, target='input_filename')
        filename = self.view.widget_get_value('input_filename')
        JSONImporter.last_folder, bn = os.path.split(filename)

    def on_btnok_clicked(self, widget):
        obj = json.load(open(self.filename))
        a = isinstance(obj, list) and obj or [obj]
        bauble.task.queue(self.run(a))

    def on_btncancel_clicked(self, widget):
        pass

    def run(self, objects):
        ## generator function. will be run as a task.
        session = db.Session()
        n = len(objects)
        for i, obj in enumerate(objects):
            try:
                db.construct_from_dict(session, obj, self.create, self.update)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.warning("could not import %s (%s: %s)" %
                               (obj, type(e).__name__, e.args))
            pb_set_fraction(float(i) / n)
            yield
        session.commit()
        try:
            from bauble import gui
            gui.get_view().update()
        except:
            pass


#
# plugin classes
#

class JSONImportTool(pluginmgr.Tool):
    category = _('Import')
    label = _('JSON')

    @classmethod
    def start(cls):
        """
        Start the JSON importer.  This tool will also reinitialize the
        plugins after importing.
        """
        s = db.Session()
        filename = os.path.join(
            paths.lib_dir(), 'plugins', 'imex', 'select_export.glade')
        presenter = JSONImporter(view=editor.GenericEditorView(
            filename, root_widget_name='select_import_dialog'))
        presenter.start()  # interact && run
        presenter.cleanup()
        s.close()


class JSONExportTool(pluginmgr.Tool):
    category = _('Export')
    label = _('JSON')

    @classmethod
    def start(cls):
        # the presenter uses the view to interact with user then
        # performs the export, if this is the case.
        s = db.Session()
        filename = os.path.join(
            paths.lib_dir(), 'plugins', 'imex', 'select_export.glade')
        presenter = JSONExporter(view=editor.GenericEditorView(
            filename, root_widget_name='select_export_dialog'))
        presenter.start()  # interact && run
        presenter.cleanup()
        s.close()
