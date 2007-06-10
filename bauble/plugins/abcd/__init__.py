#
# ABCD import/exporter
#

import os,csv
import gtk.gdk
from sqlalchemy import *
import lxml.etree as etree
import lxml._elementpath # put this here sp py2exe picks it up
from lxml.etree import Element, SubElement, ElementTree
import bauble.paths as paths
import bauble.utils as utils
from bauble.utils.log import debug
#from bauble.utils import xml_safe
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
from bauble.i18n import *
from bauble.plugins.abcd.abcd import DataSets, ABCDElement, ElementFactory
from bauble.plugins.plants.species_model import Species
from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession

# NOTE: see biocase provider software for reading and writing ABCD data
# files, already downloaded software to desktop

# TODO: should have a command line argument to create labels without starting
# the full bauble interface, after creating the labels it should automatically
# open the whatever ever view is associated with pdf files
# e.g bauble -labels "select string"
# bauble -labels "block=4"
# bauble -label "acc=1997"
#
# TODO: create label make in the tools that show a dialog with an entry
# the entry is for a search string that then returns a list of all the labels
# that'll be made with checkboxess next to them to de/select the ones you
# don't want to print, could also have a check box to select species or
# accessions so we can print labels for plants that don't have accessions,
# though this could be a problem b/c abcd data expects 'unitid' fields but
# we could have a special case just for generating labels
#

def validate(root):
    '''
    validate root against ABCD 2.06 schema
    @param root: root of an XML tree to validate against
    @type root: an lxml.etree.Element
    @returns: True or False depending if root validates correctly
    '''
    schema_file = os.path.join(paths.lib_dir(), 'plugins',
            'abcd','abcd_2.06.xsd')
    xmlschema_doc = etree.parse(schema_file)
    abcd_schema = etree.XMLSchema(xmlschema_doc)
    return abcd_schema.validate(root)

# TODO: this function needs to be renamed since we now check an object in
# the list is an Accession them we use the accession data as the UnitID, else
# we treat it as a Plant...using plants is necessary for things like making
# labels but most likely accessions are wanted if we're exchanging data, the
# only problem is that accessions don't keep status, like dead, etc.

def verify_institution(institution):
    test = lambda x: x != '' and x != None
    return test(institution.name) and test(institution.technical_contact) and \
           test(institution.email) and test(institution.contact) and \
           test(institution.code)



def plants_to_abcd(plants, authors=True):
    '''
    @param plants: a list of bauble.plugins.garden.Plant object to convert
    to valid ABCD XML
    @param authors: flag to control whether to include the authors in the
    species name
    @returns: a valid ABCD ElementTree
    '''
    import bauble.plugins.garden.institution as institution
    inst = institution.Institution()
    if not verify_institution(inst):
        msg = _('Some or all of the information about your institution or ' \
                'business is not complete. Please make sure that the ' \
                'Name, Technical Contact, Email, Contact and Institution '
                'Code fields are filled in.')
        utils.message_dialog(msg)
        institution.InstitutionEditor().start()
        return plants_to_abcd(plants, authors)

    datasets = DataSets()
    ds = ElementFactory(datasets, 'DataSet')
    tech_contacts = ElementFactory(ds, 'TechnicalContacts')
    tech_contact = ElementFactory(tech_contacts, 'TechnicalContact')

    # TODO: need to include contact information in bauble meta when
    # creating a new database

    ElementFactory(tech_contact, 'Name', text=inst.technical_contact)
    ElementFactory(tech_contact, 'Email', text=inst.email)
    cont_contacts = ElementFactory(ds, 'ContentContacts')
    cont_contact = ElementFactory(cont_contacts, 'ContentContact')
    ElementFactory(cont_contact, 'Name', text=inst.contact)
    ElementFactory(cont_contact, 'Email', text=inst.email)
    metadata = ElementFactory(ds, 'Metadata', )
    description = ElementFactory(metadata, 'Description')

    # TODO: need to get the localized language
    representation = ElementFactory(description, 'Representation',
                                    attrib={'language': 'en'})
    revision = ElementFactory(metadata, 'RevisionData')
    ElementFactory(revision, 'DateModified', text='2001-03-01T00:00:00')
    title = ElementFactory(representation, 'Title', text='TheTitle')
    units = ElementFactory(ds, 'Units')

    # build the ABCD unit
    for plant in plants:
        unit = ElementFactory(units, 'Unit')
        ElementFactory(unit, 'SourceInstitutionID', text=inst.code)

        # TODO: don't really understand the SourceID element
        ElementFactory(unit, 'SourceID', text='Bauble')
        if isinstance(plant, Accession):
            acc = plant
        else:
            acc = plant.accession

        unit_id = ElementFactory(unit, 'UnitID',
                                 text = utils.xml_safe_utf8(str(plant)))
        # TODO: metadata--<DateLastEdited>2001-03-01T00:00:00</DateLastEdited>
        identifications = ElementFactory(unit, 'Identifications')

        # scientific name identification
        identification = ElementFactory(identifications, 'Identification')
        result = ElementFactory(identification, 'Result')
        taxon_identified = ElementFactory(result, 'TaxonIdentified')
        higher_taxa = ElementFactory(taxon_identified, 'HigherTaxa')
        higher_taxon = ElementFactory(higher_taxa, 'HigherTaxon')
        higher_taxon_name = ElementFactory(higher_taxon, 'HigherTaxonName',
                  text=utils.xml_safe_utf8(acc.species.genus.family))
        higher_taxon_rank = ElementFactory(higher_taxon, 'HigherTaxonRank',
                                           text='familia')
        scientific_name = ElementFactory(taxon_identified, 'ScientificName')
        ElementFactory(scientific_name, 'FullScientificNameString',
                       text=Species.str(acc.species, authors=authors,
                                        markup=False))
        name_atomised = ElementFactory(scientific_name, 'NameAtomised')
        botanical = ElementFactory(name_atomised, 'Botanical')
        ElementFactory(botanical, 'GenusOrMonomial',
                       text=utils.xml_safe(str(acc.species.genus)))
        ElementFactory(botanical, 'FirstEpithet',
                       text=utils.xml_safe_utf8(acc.species.sp))
        if acc.species.sp_author is not None:
            ElementFactory(botanical, 'AuthorTeam',
                text=(utils.xml_safe_utf8(acc.species.sp_author)))

        # vernacular name identification
        # TODO: should we include all the vernacular names or only the default
        # one
        vernacular_name = plant.accession.species.default_vernacular_name
        if vernacular_name is not None:
            identification = ElementFactory(identifications, 'Identification')
            result = ElementFactory(identification, 'Result')
            taxon_identified = ElementFactory(result, 'TaxonIdentified')
            ElementFactory(taxon_identified, 'InformalNameString',
                           text=(utils.xml_safe_utf8(vernacular_name)))

        # TODO: handle verifiers/identifiers
        # TODO: RecordBasis
        # TODO: Gathering, make our collection records fit Gatherings
        # TODO: see BotanicalGardenUnit

    try:
        assert validate(datasets), 'ABCD data not valid'
    except AssertionError, e:
        #utils.message_dialog('ABCD data not valid')
        #utils.message_details_dialog('ABCD data not valid', etree.tostring(datasets))
        debug(etree.tostring(datasets))
        raise

    return ElementTree(datasets)



class ABCDExporter:

    def start(self, filename=None, plants=None):
        if filename == None: # no filename, ask the user
            d = gtk.FileChooserDialog("Choose a file to export to...", None,
                                      gtk.FILE_CHOOSER_ACTION_SAVE,
                                      (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                       gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
            response = d.run()
            filename = d.get_filename()
            d.destroy()
            if response != gtk.RESPONSE_ACCEPT or filename == None:
                return
        self.run(filename, plants)


    def run(self, filename, plants=None):
        if filename == None:
            raise ValueError("filename can not be None")

        # TODO: check if filename already exists give a message to the user

        # if plants is None then export all plants, this could be huge
        # TODO: do something about this, like list the number of plants
        # to be returned and make sure this is what the user wants
        if plants == None:
            session = create_session()
            plants = session.query(Plant).select()
            #plants = plugins.tables["Plant"].select()
        data = plants_to_abcd(plants)
        data.write_c14n(filename)


#class ABCDImporter:
#
#    def start(self, filenames=None):
#        pass
#
#    def run(self, filenames):
#        pass

#class ABCDImportTool(BaubleTool):
#    category = "Import"
#    label = "ABCD"
#
#    @classmethod
#    def start(cls):
#        ABCDImporter().start()


class ABCDExportTool(pluginmgr.Tool):
    category = "Export"
    label = "ABCD"

    @classmethod
    def start(cls):
        msg = 'The ABCD Exporter is not fully implemented. At the moment it '\
              'will export the plants in the database but will not include ' \
              'source information such as collection and donation data'
        utils.message_dialog(msg)
        ABCDExporter().start()


class ABCDImexPlugin(pluginmgr.Plugin):
    tools = [ABCDExportTool]
    depends = ["PlantsPlugin"]

plugin = ABCDImexPlugin


__all__ = [DataSets, ABCDElement, ElementFactory, ABCDExporter, ABCDExportTool, plants_to_abcd]
