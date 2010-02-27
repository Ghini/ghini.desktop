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
import traceback

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *

import bauble
import bauble.db as db
from bauble.utils.log import debug
import bauble.utils as utils
import bauble.utils.desktop as desktop
import bauble.paths as paths
from bauble.plugins.plants.species import Species
from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession
from bauble.plugins.abcd import create_abcd, ABCDAdapter, ABCDElement
from bauble.plugins.report import get_all_plants, get_all_species, \
     get_all_accessions, FormatterPlugin, SettingsBox


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
renderers_map = {'Apache FOP': fop_cmd + \
                               ' -fo %(fo_filename)s -pdf %(out_filename)s',
                 'XEP': 'xep -fo %(fo_filename)s -pdf %(out_filename)s',
#                 'xmlroff': 'xmlroff -o %(out_filename)s %(fo_filename)s',
#                 'Ibex for Java': 'java -cp /home/brett/bin/ibex-3.9.7.jar \
#         ibex.Run -xml %(fo_filename)s -pdf %(out_filename)s'
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
        if exe in os.listdir(p):
            return True
    return False


class SpeciesABCDAdapter(ABCDAdapter):
    """
    An adapter to convert a Species to an ABCD Unit, the SpeciesABCDAdapter
    does not create a valid ABCDUnit since we can't provide the required UnitID
    """
    def __init__(self, species, for_labels=False):
        super(SpeciesABCDAdapter, self).__init__(species)
        self.for_labels = for_labels
        self.species = species

    def get_UnitID(self):
        # **** This is makes the ABCD data NOT valid ABCD but it does make
        # it work for creating reports without including the accession or
        # plant code
        return ""

    def get_family(self):
        return utils.xml_safe_utf8(self.species.genus.family)

    def get_FullScientificNameString(self, authors=True):
        return Species.str(self.species, authors=authors,markup=False)

    def get_GenusOrMonomial(self):
        return utils.xml_safe_utf8(str(self.species.genus))

    def get_FirstEpithet(self):
        return utils.xml_safe_utf8(str(self.species.sp))

    def get_AuthorTeam(self):
        author = self.species.sp_author
        if author is None:
            return None
        else:
            return utils.xml_safe_utf8(author)

    def get_InformalNameString(self):
        vernacular_name = self.species.default_vernacular_name
        if vernacular_name is None:
            return None
        else:
            return utils.xml_safe_utf8(vernacular_name)

    def extra_elements(self, unit):
        # distribution isn't in the ABCD namespace so it should create an
        # invalid XML file
        if self.for_labels and self.species.label_distribution:
            etree.SubElement(unit, 'distribution').text=\
                self.species.label_distribution

        # TODO: reenable notes..could do a list like (date) note, (date) note
        #
        # if self.species.notes is not None:
        #     ABCDElement(unit, 'Notes',
        #                 text=utils.xml_safe(unicode(self.species.notes)))


class PlantABCDAdapter(SpeciesABCDAdapter):
    """
    An adapter to convert a Plant to an ABCD Unit
    """
    def __init__(self, plant, for_labels=False):
        super(PlantABCDAdapter, self).__init__(plant.accession.species,
                                               for_labels)
        self.plant = plant


    def get_UnitID(self):
        return utils.xml_safe_utf8(str(self.plant))


    def extra_elements(self, unit):
        bg_unit = ABCDElement(unit, 'BotanicalGardenUnit')
        ABCDElement(bg_unit, 'LocationInGarden',
                    text=utils.xml_safe_utf8(str(self.plant.location)))
        # TODO: reenable notes
        # if self.plant.notes is not None:
        #     ABCDElement(unit, 'Notes',
        #                 text=utils.xml_safe(unicode(self.plant.notes)))
        super(PlantABCDAdapter, self).extra_elements(unit)


class AccessionABCDAdapter(SpeciesABCDAdapter):
    """
    An adapter to convert a Plant to an ABCD Unit
    """
    def __init__(self, accession, for_labels=False):
        super(AccessionABCDAdapter, self).__init__(accession.species,
                                                   for_labels)
        self.accession = accession

    def get_UnitID(self):
        return utils.xml_safe_utf8(str(self.accession))


    # TODO: these values should probably alse be added for the PlantABCDAdapter
    def donation_extra_elements(self, unit):
        pass
    def collection_extra_elements(self, unit):
        pass
    def extra_elements(self, unit):
        # TODO: this needs to be updated and filled in
        return
        # TODO: reenable notes
        if self.accession.notes is not None:
            ABCDElement(unit, 'Notes',
                        text=utils.xml_safe(unicode(self.accession.notes)))
                        #text=utils.xml_safe(unicode(self.accession.notes)))
        if self.accession.source_type == 'Collection':
            # see ABCD/Unit/Gathering, CollectorsFieldNumber
            self.collection_extra_elements(unit)
        elif self.accession.source_type == 'Donation':
            # see DonorCategory, DecodedDonorInstitute
            self.donation_extra_elements(unit)
        else:
            # TODO: what should we do here
            pass
        super(AccessionABCDAdapter, self).extra_elements(unit)


class SettingsBoxPresenter(object):

    def __init__(self, widgets):
        self.widgets = widgets
        for name in renderers_map:
            self.widgets.renderer_combo.append_text(name)



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


    def get_settings(self):
        '''
        return a dict of settings from the settings box gui
        '''
        return {'stylesheet': self.widgets.stylesheet_chooser.get_filename(),
                'renderer': self.widgets.renderer_combo.get_active_text(),
                'source_type':self.widgets.source_type_combo.get_active_text(),
                'authors': self.widgets.author_check.get_active(),
                'private': self.widgets.private_check.get_active()}


    def update(self, settings):
        if 'stylesheet' in settings and settings['stylesheet'] != None:
            self.widgets.stylesheet_chooser.\
                                        set_filename(settings['stylesheet'])
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

        if 'private' in settings:
            self.widgets.private_check.set_active(settings['private'])


_settings_box = XSLFormatterSettingsBox()

class XSLFormatterPlugin(FormatterPlugin):

    title = _('XSL')

    @classmethod
    def install(cls, import_defaults=True):
	# copy default template files to user_dir
	templates = ['basic.xsl', 'labels.xsl', 'plant_list.xsl',
		     'plant_list_ex.xsl', 'small_labels.xsl']
        base_dir = os.path.join(paths.lib_dir(), "plugins", "report", 'xsl')
	for template in templates:
	    f = os.path.join(paths.user_dir(), template)
	    if not os.path.exists(f):
		shutil.copy(os.path.join(base_dir, template), f)


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
            utils.message_dialog(_('Could not find the command "%(exe)s" to ' \
                                       'start the %(renderer_name)s '\
                                       'renderer.') % \
                                     ({'exe': exe, 'renderer_name': renderer}),
                                 gtk.MESSAGE_ERROR)
            return False

        session = db.Session()

        # convert objects to ABCDAdapters depending on source type for
        # passing to create_abcd
        adapted = []
        if source_type == plant_source_type:
            plants = sorted(get_all_plants(objs, session=session),
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
            species = sorted(get_all_species(objs, session=session),
                             key=utils.natsort_key)
            if len(species) == 0:
                utils.message_dialog(_('There are no species in the search '
                                       'results.  Please try another search.'))
                return False
            for s in species:
                adapted.append(SpeciesABCDAdapter(s, for_labels=True))
        elif source_type == accession_source_type:
            accessions = sorted(get_all_accessions(objs, session=session),
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

#        debug(etree.dump(abcd_data.getroot()))

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
#        print fo_cmd
#        debug(fo_cmd)
        # TODO: use popen to get output
        os.system(fo_cmd)

#        print filename
        if not os.path.exists(filename):
            utils.message_dialog(_('Error creating the PDF file. Please ' \
                                   'ensure that your PDF formatter is ' \
                                   'properly installed.'), gtk.MESSAGE_ERROR)
            return False
        else:
            try:
                desktop.open(filename)
            except OSError:
                utils.message_dialog(_('Could not open the report with the '\
                                       'default program. You can open the '\
                                       'file manually at %s') % filename)

        return True


# expose the formatter
try:
    import lxml.etree as etree
except ImportError:
    utils.message_dialog('The <i>lxml</i> package is required for the '\
                         'XSL report plugin')
else:
    formatter_plugin = XSLFormatterPlugin
