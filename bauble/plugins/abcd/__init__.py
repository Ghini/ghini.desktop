#
# ABCD import/exporter
#

import os,csv
import gtk.gdk
from sqlalchemy import *
from sqlalchemy.orm import *
import lxml.etree as etree
import lxml._elementpath # put this here sp py2exe picks it up
from lxml.etree import Element, SubElement, ElementTree
import bauble
import bauble.paths as paths
import bauble.utils as utils
from bauble.utils.log import debug
#from bauble.utils import xml_safe
import bauble.utils as utils
import bauble.pluginmgr as pluginmgr
from bauble.i18n import *
from bauble.plugins.abcd.abcd import DataSets, ABCDElement#, ElementFactory
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


class ABCDAdapter(object):

    # TODO: create a HigherTaxonRank/HigherTaxonName iteratorator for a list
    # of all the higher taxon

    # TODO: need to mark those fields that are required and those that
    # are optional
    def extra_elements(self, unit):
        """
        add extra non required elements
        """
        pass

    def __init__(self, obj):
        self._object = obj
        self._mapper = object_mapper(self._object)

    def get_UnitID(self):
        pass

    def get_family(self):
        pass

    def get_FullScientificNameString(self, authors=True):
        pass

    def get_GenusOrMonomial(self):
        pass

    def get_FirstEpithet(self):
        pass

    def get_AuthorTeam(self):
        pass

    def get_InformalNameString(self):
        pass

    def get_dbURI(self):
        # db://user@host:password/database/table/id
        url = str(self._mapper.local_table.metadata.bind.url)
        # parse out the password
        at_i = url.find('@')
        if at_i != -1:
            col_i = url.find(':')
            i = url.find(':', col_i+1, at_i)
            url = url[:i] + url[at_i:]
        return '%s/%s/%s' % (url, self._mapper.local_table,
                             self._object.id)



def create_abcd(decorated_objects, authors=True, validate=True):
    '''
    @param objects: a list/tuple of objects that implement the ABCDDecorator
    interface
    @param authors: flag to control whether to include the authors in the
    species name
    @param validate: whether we should valid the data before returning
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
    ds = ABCDElement(datasets, 'DataSet')
    tech_contacts = ABCDElement(ds, 'TechnicalContacts')
    tech_contact = ABCDElement(tech_contacts, 'TechnicalContact')

    # TODO: need to include contact information in bauble meta when
    # creating a new database
    ABCDElement(tech_contact, 'Name', text=inst.technical_contact)
    ABCDElement(tech_contact, 'Email', text=inst.email)
    cont_contacts = ABCDElement(ds, 'ContentContacts')
    cont_contact = ABCDElement(cont_contacts, 'ContentContact')
    ABCDElement(cont_contact, 'Name', text=inst.contact)
    ABCDElement(cont_contact, 'Email', text=inst.email)
    metadata = ABCDElement(ds, 'Metadata', )
    description = ABCDElement(metadata, 'Description')

    # TODO: need to get the localized language
    representation = ABCDElement(description, 'Representation',
                                    attrib={'language': 'en'})
    revision = ABCDElement(metadata, 'RevisionData')
    ABCDElement(revision, 'DateModified', text='2001-03-01T00:00:00')
    title = ABCDElement(representation, 'Title', text='TheTitle')
    units = ABCDElement(ds, 'Units')

    # build the ABCD unit
    for obj in decorated_objects:
        unit = ABCDElement(units, 'Unit')
        ABCDElement(unit, 'SourceInstitutionID', text=inst.code)

        # TODO: don't really understand the SourceID element
        ABCDElement(unit, 'SourceID', text='Bauble')

        unit_id = ABCDElement(unit, 'UnitID', text=obj.get_UnitID())
        # TODO: metadata--<DateLastEdited>2001-03-01T00:00:00</DateLastEdited>
        identifications = ABCDElement(unit, 'Identifications')

        # scientific name identification
        identification = ABCDElement(identifications, 'Identification')
        result = ABCDElement(identification, 'Result')
        taxon_identified = ABCDElement(result, 'TaxonIdentified')
        higher_taxa = ABCDElement(taxon_identified, 'HigherTaxa')
        higher_taxon = ABCDElement(higher_taxa, 'HigherTaxon')

        # TODO: ABCDDecorator should provide an iterator so that we can
        # have multiple HigherTaxonName's
        higher_taxon_name = ABCDElement(higher_taxon, 'HigherTaxonName',
                                           text=obj.get_family())
        higher_taxon_rank = ABCDElement(higher_taxon, 'HigherTaxonRank',
                                           text='familia')

        scientific_name = ABCDElement(taxon_identified, 'ScientificName')
        ABCDElement(scientific_name, 'FullScientificNameString',
                       text=obj.get_FullScientificNameString(authors))

        name_atomised = ABCDElement(scientific_name, 'NameAtomised')
        botanical = ABCDElement(name_atomised, 'Botanical')
        ABCDElement(botanical, 'GenusOrMonomial',
                       text=obj.get_GenusOrMonomial())
        ABCDElement(botanical, 'FirstEpithet', text=obj.get_FirstEpithet())
        author_team = obj.get_AuthorTeam()
        if author_team is not None:
            ABCDElement(botanical, 'AuthorTeam', text=author_team)

        # vernacular name identification
        # TODO: should we include all the vernacular names or only the default
        # one
        vernacular_name = obj.get_InformalNameString()
        if vernacular_name is not None:
            identification = ABCDElement(identifications, 'Identification')
            result = ABCDElement(identification, 'Result')
            taxon_identified = ABCDElement(result, 'TaxonIdentified')
            ABCDElement(taxon_identified, 'InformalNameString',
                           text=vernacular_name)

        dburi = obj.get_dbURI()
        if dburi is not None:
            ABCDElement(unit, "Notes", text=dburi)

        # add all the extra non standard elements
        obj.extra_elements(unit)
        # TODO: handle verifiers/identifiers
        # TODO: RecordBasis
        # TODO: Gathering, make our collection records fit Gatherings
        # TODO: see BotanicalGardenUnit

    if not validate:
        return ElementTree(datasets)

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
            plants = bauble.Session().query(Plant)
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


__all__ = [DataSets, ABCDElement, #ElementFactory,
           ABCDExporter, ABCDExportTool, create_abcd]
