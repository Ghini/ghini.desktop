#
# default report formatter package
#
"""
The PDF report generator module.

This module takes a list of objects, get all the plants from the
objects, converts them to the ABCD XML format, transforms the ABCD
data to an XSL formatting stylesheet and uses a XSL-PDF renderer to
convert the stylesheet to PDF.
"""
import sys, os, tempfile, traceback
import gtk
from sqlalchemy import *
import bauble
from bauble.utils.log import debug
import bauble.utils as utils
import bauble.utils.desktop as desktop
import bauble.paths as paths
from bauble.i18n import *
from bauble.plugins.plants.species import Species, species_table
from bauble.plugins.garden.plant import Plant, plant_table, plant_delimiter
from bauble.plugins.garden.accession import Accession, accession_table
from bauble.plugins.abcd import create_abcd, ABCDAdapter
from bauble.plugins.report import get_all_plants, get_all_species, \
     FormatterPlugin, SettingsBox


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

class PlantABCDAdapter(ABCDAdapter):

    def __init__(self, plant):
        self.plant = plant
        self.species = self.plant.accession.species

    def get_UnitID(self):
        return utils.xml_safe_utf8(str(self.plant))

    def get_family(self):
        return utils.xml_safe_utf8(self.species.genus.family)

    def get_FullScientificNameString(self, authors=True):
        return Species.str(self.species,authors=authors,markup=False)

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


class SpeciesABCDAdapter:

    def __init__(self, species):
        self.species = species

    def get_UnitID(self):
        # **** This is makes the ABCD data NOT valid ABCD but it does make
        # it work for created reports without including the accession or
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


class SettingsBoxPresenter:

    def __init__(self, widgets):
        self.widgets = widgets
        model = gtk.ListStore(str)
        for name in renderers_map:
            model.append([name])
        self.widgets.renderer_combo.set_model(model)



class DefaultFormatterSettingsBox(SettingsBox):

    def __init__(self, report_dialog=None, *args):
        super(DefaultFormatterSettingsBox, self).__init__(*args)
        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(),
                               "plugins", "report", 'default', 'gui.glade'))
        # keep a refefence to settings box so it doesn't get destroyed in
        # remove_parent()
        settings_box = self.widgets.settings_box
        self.widgets.remove_parent(self.widgets.settings_box)
        self.pack_start(settings_box)
        self.presenter = SettingsBoxPresenter(self.widgets)


    def get_settings(self):
        '''
        return a dict of settings from the settings box gui
        '''
        return {'stylesheet': self.widgets.stylesheet_chooser.get_filename(),
                'renderer': self.widgets.renderer_combo.get_active_text(),
                'source_type':self.widgets.source_type_combo.get_active_text(),
                'authors': self.widgets.author_check.get_active()}


    def update(self, settings={}):
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


_settings_box = DefaultFormatterSettingsBox()

class DefaultFormatterPlugin(FormatterPlugin):

    title = _('Default')

    @staticmethod
    def get_settings_box():
        return DefaultFormatterSettingsBox()


    @staticmethod
    def format(objs, **kwargs):
#        debug('format(%s)' % kwargs)
        stylesheet = kwargs['stylesheet']
        authors = kwargs['authors']
        renderer = kwargs['renderer']
        source_type = kwargs['source_type']
        error_msg = None
        if not stylesheet:
            error_msg = _('Please select a stylesheet.')
        elif not renderer:
            error_msg = _('Please select a a renderer')
        if error_msg is not None:
            utils.message_dialog(error_msg, gtk.MESSAGE_WARNING)
            return False

        fo_cmd = renderers_map[renderer]
        session = bauble.Session()

        adapted = []
        if source_type == plant_source_type:
            plants = get_all_plants(objs, session=session)
            plants.sort(cmp=lambda x, y: cmp(str(x), str(y)))
            if len(plants) == 0:
                utils.message_dialog(_('There are no plants in the search '
                                       'results.  Please try another search.'))
                return False
            for p in plants:
                adapted.append(PlantABCDAdapter(p))
        elif source_type == species_source_type:
            species = get_all_species(objs, session=session)
            species.sort(cmp=lambda x,y: cmp(str(x), str(y)))
            if len(species) == 0:
                utils.message_dialog(_('There are no species in the search '
                                       'results.  Please try another search.'))
                return False
            for s in species:
                adapted.append(SpeciesABCDAdapter(s))
        else:
            raise NotImplementedError('unknown source_type: %s' % source_type)
        if len(adapted) == 0:
            raise Exception # shouldn't ever really get here
        abcd_data = create_abcd(adapted, authors=authors, validate=False)

        session.clear() # we don't need the plants anymore

        # this adds a "distribution" tag from the species_distribnution, we
        # use this when generating labels and can be safely ignored since it's
        # not in the ABCD namespace
        for el in abcd_data.getiterator(tag='{http://www.tdwg.org/schemas/abcd/2.06}Unit'):
            unit_id = el.xpath('abcd:UnitID',
                            {'abcd': 'http://www.tdwg.org/schemas/abcd/2.06'})


            # TODO: ***** right now we only set the distribution if we are
            # using a plant_source_type but we should be able to get
            # distributions from others, the problem is how to we get
            # a unique id when we are generating the abcd from species
            if source_type == plant_source_type:
                code = unit_id[0].text
                results = session.query(Species).select(and_(species_table.c.id==accession_table.c.species_id, accession_table.c.code == code))

                if len(results) < 1:
                    acc_code, plant_code = code.rsplit(plant_delimiter(), 1)
                    results = session.query(Species).select(and_(species_table.c.id==accession_table.c.species_id, accession_table.c.id==plant_table.c.accession_id, accession_table.c.code==acc_code, plant_table.c.code==plant_code))

                if len(results) < 1:
                    raise ValueError(_('Couldn\'t find a Plant or Accession '\
                                       'with code %s') % code)
                species = results[0]
##             elif source_type == species_source_type:
##                 if species.distribution is not None:
##                     etree.SubElement(el, 'distribution').text=\
##                                          species.distribution_str()
                if species.distribution is not None:
                    etree.SubElement(el, 'distribution').text=\
                                         species.distribution_str()
            session.clear()
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
                                 'properly_installed'), gtk.MESSAGE_ERROR)
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
                         'default report plugins')
else:
    formatter_plugin = DefaultFormatterPlugin
