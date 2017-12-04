# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
#
# xsl report formatter package
#
"""
The PDF report generator module.

This module takes a list of objects, get all the plants from the
objects, converts them to the ABCD XML format, transforms the ABCD
data to an XSL formatting stylesheet and uses a XSL-PDF renderer to
convert the stylesheet to PDF.
"""
import shutil
import sys
import os
import tempfile

import gtk

import logging
logger = logging.getLogger(__name__)

#from sqlalchemy import *
from sqlalchemy.orm import object_session

import bauble.db as db
import bauble.paths as paths
from bauble.plugins.plants.species import Species
#from bauble.plugins.garden.plant import Plant
#from bauble.plugins.garden.accession import Accession
from bauble.plugins.abcd import create_abcd, ABCDAdapter, ABCDElement
from bauble.plugins.report import (
    get_plants_pertinent_to, get_species_pertinent_to,
    get_accessions_pertinent_to, FormatterPlugin, SettingsBox)
import bauble.prefs as prefs
import bauble.utils as utils
import bauble.utils.desktop as desktop


if sys.platform == "win32":
    fop_cmd = 'fop.bat'
else:
    fop_cmd = 'fop'

# Bugs:
# https://bugs.launchpad.net/bauble/+bug/104963 (check for PDF renderers on PATH)
#

# TODO: need to make sure we can't select the OK button if we haven't selected
# a value for everything

# TODO: use which() to search the path for a known renderer, could do this in
# task so that it's non blocking, should cache the values in the prefs and
# check that they are still valid when we open the report UI up again
#def which(e):
#    return ([os.path.join(p, e) for p in os.environ['PATH'].split(os.pathsep) if os.path.exists(os.path.join(p, e))] + [None])[0]

# TODO: support FOray, see http://www.foray.org/
renderers_map = {'Apache FOP': (fop_cmd + ' -fo %(fo_filename)s '
                                '-pdf %(out_filename)s'),
                 'XEP': 'xep -fo %(fo_filename)s -pdf %(out_filename)s',
                 # 'xmlroff': 'xmlroff -o %(out_filename)s %(fo_filename)s',
                 # 'Ibex for Java': 'java -cp /home/brett/bin/ibex-3.9.7.jar
                 # ibex.Run -xml %(fo_filename)s -pdf %(out_filename)s'
                 }
default_renderer = 'Apache FOP'

plant_source_type = _('Plant/Clone')
accession_source_type = _('Accession')
species_source_type = _('Species')
default_source_type = plant_source_type


def on_path(exe):
    # TODO: is the PATH variable used on non-english systems
    PATH = os.environ['PATH']
    if not PATH:
        return False
    for p in PATH.split(os.pathsep):
        try:
            # handle exceptions in case the path doesn't exist
            if exe in os.listdir(p):
                return True
        except:
            pass
    return False


class SpeciesABCDAdapter(ABCDAdapter):
    """
    An adapter to convert a Species to an ABCD Unit, the SpeciesABCDAdapter
    does not create a valid ABCDUnit since we can't provide the required UnitID
    """
    def __init__(self, species, for_labels=False):
        super(SpeciesABCDAdapter, self).__init__(species)

        # hold on to the accession so it doesn't get cleaned up and closed
        self.session = object_session(species)
        self.for_labels = for_labels
        self.species = species
        self._date_format = prefs.prefs[prefs.date_format_pref]

    def get_UnitID(self):
        # **** Returning the empty string for the UnitID makes the
        # ABCD data NOT valid ABCD but it does make it work for
        # creating reports without including the accession or plant
        # code
        return ""

    def get_DateLastEdited(self):
        return utils.xml_safe(self.species._last_updated.isoformat())

    def get_family(self):
        return utils.xml_safe(self.species.genus.family)

    def get_FullScientificNameString(self, authors=True):
        s = self.species.str(authors=authors, markup=False)
        return utils.xml_safe(s)

    def get_GenusOrMonomial(self):
        return utils.xml_safe(str(self.species.genus))

    def get_FirstEpithet(self):
        return utils.xml_safe(str(self.species.sp))

    def get_AuthorTeam(self):
        author = self.species.sp_author
        if author is None:
            return None
        else:
            return utils.xml_safe(author)

    def get_InfraspecificAuthor(self):
        return utils.xml_safe(str(self.species.infraspecific_author))

    def get_InfraspecificRank(self):
        return utils.xml_safe(str(self.species.infraspecific_rank))

    def get_InfraspecificEpithet(self):
        return utils.xml_safe(str(self.species.infraspecific_epithet))
    
    def get_CultivarName(self):
        return utils.xml_safe(str(self.species.cultivar_epithet))

    def get_HybridFlag(self):
        if self.species.hybrid is True:
            return utils.xml_safe(str(self.species.hybrid_char))
        else:
            return None

    def get_InformalNameString(self):
        vernacular_name = self.species.default_vernacular_name
        if vernacular_name is None:
            return None
        else:
            return utils.xml_safe(vernacular_name)

    def get_Notes(self):
        if not self.species.notes:
            return None
        notes = []
        for note in self.species.notes:
            notes.append(dict(date=utils.xml_safe(note.date.isoformat()),
                              user=utils.xml_safe(note.user),
                              category=utils.xml_safe(note.category),
                              note=utils.xml_safe(note.note)))
        return utils.utf8(notes)

    def extra_elements(self, unit):
        # distribution isn't in the ABCD namespace so it should create an
        # invalid XML file
        if self.for_labels:
            if self.species.label_distribution:
                etree.SubElement(unit, 'distribution').text = \
                    self.species.label_distribution
            elif self.species.distribution:
                etree.SubElement(unit, 'distribution').text = \
                    self.species.distribution_str()


class AccessionABCDAdapter(SpeciesABCDAdapter):
    """
    An adapter to convert a Plant to an ABCD Unit
    """
    def __init__(self, accession, for_labels=False):
        super(AccessionABCDAdapter, self).__init__(accession.species,
                                                   for_labels)
        self.accession = accession

    def get_UnitID(self):
        return utils.xml_safe(str(self.accession))

    def get_FullScientificNameString(self, authors=True):
        s = self.accession.species_str(authors=authors, markup=False)
        return utils.xml_safe(s)
    
    def get_IdentificationQualifier(self):
        idqual=self.accession.id_qual
        if idqual is None:
            return None
        else:
            return utils.xml_safe(idqual)
        
    def get_IdentificationQualifierRank(self):
        idqrank=self.accession.id_qual_rank
        if idqrank is None:
            return None
        else:
            return utils.xml_safe(idqrank)
        
    def get_DateLastEdited(self):
        return utils.xml_safe(self.accession._last_updated.isoformat())

    def get_Notes(self):
        if not self.accession.notes:
            return None
        notes = []
        for note in self.accession.notes:
            notes.append(dict(date=utils.xml_safe(note.date.isoformat()),
                              user=utils.xml_safe(note.user),
                              category=utils.xml_safe(note.category),
                              note=utils.xml_safe(note.note)))
        return utils.xml_safe(notes)

    def extra_elements(self, unit):
        super(AccessionABCDAdapter, self).extra_elements(unit)
        if self.for_labels:
            if self.species.label_distribution:
                etree.SubElement(unit, 'distribution').text = \
                    self.species.label_distribution
            elif self.species.distribution:
                etree.SubElement(unit, 'distribution').text = \
                    self.species.distribution_str()

        if self.accession.source and self.accession.source.collection:
            collection = self.accession.source.collection
            utf8 = utils.xml_safe
            gathering = ABCDElement(unit, 'Gathering')

            if collection.collectors_code:
                ABCDElement(gathering, 'Code',
                            text=utf8(collection.collectors_code))

            # TODO: get date pref for DayNumberBegin
            if collection.date:
                date_time = ABCDElement(gathering, 'DateTime')
                ABCDElement(date_time, 'DateText',
                            utils.xml_safe(collection.date.isoformat()))

            if collection.collector:
                agents = ABCDElement(gathering, 'Agents')
                agent = ABCDElement(agents, 'GatheringAgent')
                ABCDElement(agent, 'AgentText',
                            text=utf8(collection.collector))

            if collection.locale:
                ABCDElement(gathering, 'LocalityText',
                            text=utf8(collection.locale))

            if collection.region:
                named_areas = ABCDElement(gathering, 'NamedAreas')
                named_area = ABCDElement(named_areas, 'NamedArea')
                ABCDElement(named_area, 'AreaName',
                            text=utf8(collection.region))

            if collection.habitat:
                ABCDElement(gathering, 'AreaDetail',
                            text=utf8(collection.habitat))

            if collection.longitude or collection.latitude:
                site_coords = ABCDElement(gathering, 'SiteCoordinateSets')
                coord = ABCDElement(site_coords, 'SiteCoordinates')
                lat_long = ABCDElement(coord, 'CoordinatesLatLong')
                ABCDElement(lat_long, 'LongitudeDecimal',
                            text=utf8(collection.longitude))
                ABCDElement(lat_long, 'LatitudeDecimal',
                            text=utf8(collection.latitude))
                if collection.gps_datum:
                    ABCDElement(lat_long, 'SpatialDatum',
                                text=utf8(collection.gps_datum))
                if collection.geo_accy:
                    ABCDElement(coord, 'CoordinateErrorDistanceInMeters',
                                text=utf8(collection.geo_accy))

            if collection.elevation:
                altitude = ABCDElement(gathering, 'Altitude')
                if collection.elevation_accy:
                    text = '%sm (+/- %sm)' % (collection.elevation,
                                              collection.elevation_accy)
                else:
                    text = '%sm' % collection.elevation
                ABCDElement(altitude, 'MeasurementOrFactText', text=text)

            if collection.notes:
                ABCDElement(gathering, 'Notes', utf8(collection.notes))


class PlantABCDAdapter(AccessionABCDAdapter):
    """
    An adapter to convert a Plant to an ABCD Unit
    """
    def __init__(self, plant, for_labels=False):
        super(PlantABCDAdapter, self).__init__(plant.accession, for_labels)
        self.plant = plant

    def get_UnitID(self):
        return utils.xml_safe(str(self.plant))

    def get_DateLastEdited(self):
        return utils.xml_safe(self.plant._last_updated.isoformat())

    def get_Notes(self):
        if not self.plant.notes:
            return None
        notes = []
        for note in self.plant.notes:
            notes.append(dict(date=utils.xml_safe(note.date.isoformat()),
                              user=utils.xml_safe(note.user),
                              category=utils.xml_safe(note.category),
                              note=utils.xml_safe(note.note)))
        return utils.xml_safe(str(notes))

    def extra_elements(self, unit):
        bg_unit = ABCDElement(unit, 'BotanicalGardenUnit')
        ABCDElement(bg_unit, 'AccessionSpecimenNumbers',
                    text=utils.xml_safe(self.plant.quantity))
        ABCDElement(bg_unit, 'LocationInGarden',
                    text=utils.xml_safe(str(self.plant.location)))
        if self.for_labels:
            if self.species.label_distribution:
                etree.SubElement(unit, 'distribution').text = \
                    self.species.label_distribution
            elif self.species.distribution:
                etree.SubElement(unit, 'distribution').text = \
                    self.species.distribution_str()
        # TODO: AccessionStatus, AccessionMaterialtype,
        # ProvenanceCategory, AccessionLineage, DonorCategory,
        # PlantingDate, Propagation
        super(PlantABCDAdapter, self).extra_elements(unit)


class SettingsBoxPresenter(object):

    def __init__(self, widgets):
        self.widgets = widgets
        for name in renderers_map:
            self.widgets.renderer_combo.append_text(name)


# TODO: could make this look more a gtk.FileChooserButton but make it
# an hbox and adding the separator and file icon
class FileChooserButton(gtk.Button):
    """
    Create our own basic FileChooserButton to work around the issue that
    if you click the gtk.FileChooseButton the label gets reset to "None"
    but doesn't revert back to the original file of the dialog is cancelled.
    """

    _default_label = _("Select a file…")

    def __init__(self, dialog_parent):
        super(FileChooserButton, self).__init__(self._default_label)
        self._filename = False
        self.props.use_underline = False
        self.props.xalign = 0
        self.dialog = \
            gtk.FileChooserDialog(title=_('Select a stylesheet'),
                                  parent=dialog_parent,
                                  buttons=(
                                      gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                      gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.dialog.set_select_multiple(False)
        self.dialog.set_current_folder(paths.appdata_dir())
        self.dialog.connect('response', self._on_response)
        self.connect('clicked', self._on_clicked)

    def _on_clicked(self, *args):
        self.dialog.run()
        self.dialog.hide()

    def _on_response(self, dialog, response):
        if response == gtk.RESPONSE_ACCEPT:
            self.set_filename(self.dialog.get_filename())

    def get_filename(self):
        return self._filename

    def set_filename(self, filename):
        if not filename:
            self._filename = None
            self.dialog.set_filename('')
            self.dialog.set_current_folder(paths.appdata_dir())
            self.props.label = self._default_label
        else:
            self._filename = filename
            head, tail = os.path.split(self._filename)
            self.dialog.set_filename(self._filename)
            self.props.label = tail


class XSLFormatterSettingsBox(SettingsBox):

    def __init__(self, report_dialog=None, *args):
        super(XSLFormatterSettingsBox, self).__init__(*args)
        filename = os.path.join(paths.lib_dir(), "plugins", "report", 'xsl',
                                'gui.glade')
        self.widgets = utils.load_widgets(filename)

        utils.setup_text_combobox(self.widgets.renderer_combo)

        combo = self.widgets.source_type_combo
        values = [_('Accession'), _('Plant/Clone'), _('Species')]
        utils.setup_text_combobox(combo, values=values)

        # keep a refefence to settings box so it doesn't get destroyed in
        # remove_parent()
        self.settings_box = self.widgets.settings_box
        self.widgets.remove_parent(self.widgets.settings_box)
        self.pack_start(self.settings_box)
        self.presenter = SettingsBoxPresenter(self.widgets)

        self.stylesheet_chooser = FileChooserButton(
            dialog_parent=report_dialog)
        self.widgets.stylesheet_alignment.add(self.stylesheet_chooser)

    def get_settings(self):
        '''
        return a dict of settings from the settings box gui
        '''
        return {
            'stylesheet': self.stylesheet_chooser.get_filename(),
            'renderer': self.widgets.renderer_combo.get_active_text(),
            'source_type': self.widgets.source_type_combo.get_active_text(),
            'authors': self.widgets.author_check.get_active(),
            'private': self.widgets.private_check.get_active()}

    def update(self, settings):
        if 'stylesheet' in settings and settings['stylesheet'] is not None:
            self.stylesheet_chooser.set_filename(settings['stylesheet'])
        else:
            self.stylesheet_chooser.set_filename(None)

        if 'renderer' not in settings:
            utils.combo_set_active_text(self.widgets.renderer_combo,
                                        default_renderer)
        else:
            utils.combo_set_active_text(self.widgets.renderer_combo,
                                        settings['renderer'])

        if 'source_type' not in settings:
            utils.combo_set_active_text(self.widgets.source_type_combo,
                                        default_source_type)
        else:
            utils.combo_set_active_text(self.widgets.source_type_combo,
                                        settings['source_type'])

        if 'authors' in settings:
            self.widgets.author_check.set_active(settings['authors'])
        else:
            self.widgets.author_check.set_active(False)

        if 'private' in settings:
            self.widgets.private_check.set_active(settings['private'])
        else:
            self.widgets.private_check.set_active(False)


_settings_box = XSLFormatterSettingsBox()


class XSLFormatterPlugin(FormatterPlugin):

    title = _('XSL')

    @classmethod
    def install(cls, import_defaults=True):
        "create templates dir on plugin installation"
        logger.debug("installing xsl plugin")
        container_dir = os.path.join(paths.appdata_dir(), "templates")
        if not os.path.exists(container_dir):
            os.mkdir(container_dir)
        cls.plugin_dir = os.path.join(paths.appdata_dir(), "templates", "xsl")
        if not os.path.exists(cls.plugin_dir):
            os.mkdir(cls.plugin_dir)

    @classmethod
    def init(cls):
        """copy default template files to appdata_dir

        we do this in the initialization instead of installation
        because new version of plugin might provide new templates.

        """
        cls.install()  # plugins still not versioned...

        templates = ['basic.xsl', 'labels.xsl', 'plant_list.xsl',
                     'plant_list_ex.xsl', 'small_labels.xsl']
        src_dir = os.path.join(paths.lib_dir(), "plugins", "report", 'xsl')
        for template in templates:
            src = os.path.join(src_dir, template)
            dst = os.path.join(cls.plugin_dir, template)
            if not os.path.exists(dst) and os.path.exists(src):
                shutil.copy(src, dst)

    @staticmethod
    def get_settings_box():
        return _settings_box

    @staticmethod
    def format(objs, **kwargs):
#        debug('format(%s)' % kwargs)
        stylesheet = kwargs['stylesheet']
        authors = kwargs['authors']
        renderer = kwargs['renderer']
        source_type = kwargs['source_type']
        use_private = kwargs['private']
        error_msg = None
        if not stylesheet:
            error_msg = _('Please select a stylesheet.')
        elif not renderer:
            error_msg = _('Please select a a renderer')
        if error_msg is not None:
            utils.message_dialog(error_msg, gtk.MESSAGE_WARNING)
            return False

        fo_cmd = renderers_map[renderer]
        exe = fo_cmd.split(' ')[0]
        if not on_path(exe):
            utils.message_dialog(_('Could not find the command "%(exe)s" to '
                                   'start the %(renderer_name)s '
                                   'renderer.') %
                                  ({'exe': exe, 'renderer_name': renderer}),
                                 gtk.MESSAGE_ERROR)
            return False

        session = db.Session()

        # convert objects to ABCDAdapters depending on source type for
        # passing to create_abcd
        adapted = []
        if source_type == plant_source_type:
            plants = sorted(get_plants_pertinent_to(objs, session=session),
                            key=utils.natsort_key)
            if len(plants) == 0:
                utils.message_dialog(_('There are no plants in the search '
                                       'results.  Please try another search.'))
                return False
            for p in plants:
                if use_private:
                    adapted.append(PlantABCDAdapter(p, for_labels=True))
                elif not p.accession.private:
                    adapted.append(PlantABCDAdapter(p, for_labels=True))
        elif source_type == species_source_type:
            species = sorted(get_species_pertinent_to(objs, session=session),
                             key=utils.natsort_key)
            if len(species) == 0:
                utils.message_dialog(_('There are no species in the search '
                                       'results.  Please try another search.'))
                return False
            for s in species:
                adapted.append(SpeciesABCDAdapter(s, for_labels=True))
        elif source_type == accession_source_type:
            accessions = sorted(get_accessions_pertinent_to(objs,
                                                            session=session),
                                key=utils.natsort_key)
            if len(accessions) == 0:
                utils.message_dialog(_('There are no accessions in the search '
                                       'results.  Please try another search.'))
                return False
            for a in accessions:
                if use_private:
                    adapted.append(AccessionABCDAdapter(a, for_labels=True))
                elif not a.private:
                    adapted.append(AccessionABCDAdapter(a, for_labels=True))
        else:
            raise NotImplementedError('unknown source type')

        if len(adapted) == 0:
            # nothing adapted....possibly everything was private
            # TODO: if everything was private and that is really why we got
            # here then it is probably better to show a dialog with a message
            # and raise and exception which appears as an error
            raise Exception('No objects could be adapted to ABCD units.')
        abcd_data = create_abcd(adapted, authors=authors, validate=False)

        session.close()

        logger.debug(etree.dump(abcd_data.getroot()))

        # create xsl fo file
        dummy, fo_filename = tempfile.mkstemp()
        style_etree = etree.parse(stylesheet)
        transform = etree.XSLT(style_etree)
        result = transform(abcd_data)
        fo_outfile = open(fo_filename, 'w')
        fo_outfile.write(str(result))
        fo_outfile.close()
        dummy, filename = tempfile.mkstemp()
        filename = '%s.pdf' % filename

        # TODO: checkout pyexpect for spawning processes

        # run the report to produce the pdf file, the command has to be
        # on the path for this to work
        fo_cmd = fo_cmd % ({'fo_filename': fo_filename,
                            'out_filename': filename})
        logger.debug(fo_cmd)
        # TODO: use popen to get output
        os.system(fo_cmd)

        logger.debug(filename)
        if not os.path.exists(filename):
            utils.message_dialog(_('Error creating the PDF file. Please '
                                   'ensure that your PDF formatter is '
                                   'properly installed.'), gtk.MESSAGE_ERROR)
            return False
        else:
            try:
                desktop.open(filename)
            except OSError:
                utils.message_dialog(_('Could not open the report with the '
                                       'default program. You can open the '
                                       'file manually at %s') % filename)

        return True


# expose the formatter
try:
    import lxml.etree as etree
except ImportError:
    utils.message_dialog('The <i>lxml</i> package is required for the '
                         'XSL report plugin')
else:
    formatter_plugin = XSLFormatterPlugin
