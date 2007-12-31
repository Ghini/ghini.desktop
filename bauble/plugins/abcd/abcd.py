#
# abcd.py
#
# module for read and writing Access to Biological Collection
# Data (ABCD) files
#

import string
from string import Template
from bauble.utils.log import log, debug
import xml.sax.saxutils
import lxml.etree as etree
from lxml.etree import Element, SubElement, ElementTree
from bauble.utils import xml_safe

# TODO: also need ability to dump to darwin core, should consider just writing
# an xsl transformation to do the conversion instead of writing more export
# code, Darwin Core is a flat structure and from i understand doesn't have a
# sense of "unit"

# TODO: doesn't validate unless i write the dataset to a file and read it back
# in, it's most likely some sort of namespace issue

namespaces = {'abcd': 'http://www.tdwg.org/schemas/abcd/2.06'}


def ABCDElement(parent, name, text=None, attrib={}):
    """
    create an ABCDElement, must be a subelement
    @param parent:
    @param name:
    @param text:
    @param attrib:
    """
    el = SubElement(parent, '{%s}%s' % (namespaces['abcd'], name),
                    nsmap=namespaces, attrib=attrib)
    el.text = text
    return el


def DataSets():
    return Element('{%s}DataSets' % namespaces['abcd'], nsmap=namespaces)


## def ElementFactory(parent, name, **kwargs):
##     """
##     @param parent: name is first checked to make sure that parent is a valid
##     parent
##     @param name: the name of the element to create, must be a valid
##     ABCD element
##     """
##     assert name in element_map, 'Unknown element: %s' % name
##     nslen = len('{%s}' % namespaces[abcd])
##     # make sure parent can is an allowed parent for name
##     assert parent.tag[nslen:] in element_map[name], parent.tag
##     el = ABCDElement(parent, name, **kwargs)
##     return el


## #
## # a map of ABCD elements to their parents
## #
## # {tagname: parents}
## element_map = {'DataSet': ['{http://www.tdwg.org/schemas/abcd/2.06}DataSets',
##                            'DataSets'],
##                    'TechnicalContacts': ['DataSet'],
##                        'TechnicalContact': ['TechnicalContacts'],
##                    'ContentContacts': ['DataSet'],
##                        'ContentContact': ['ContentContacts'],
##                    'Name': ['TechnicalContact','ContentContact'],
##                    'Email': ['TechnicalContact','ContentContact'],
##                'Metadata': ['DataSet'],
##                    'Description': ['Metadata'],
##                    'Representation': ['Description'], # language attribute
##                        'Title': ['Representation'],
##                    'RevisionData': ['Metadata'],
##                        'DateModified': ['RevisionData'],
##                'Units': ['DataSet'],
##                    'Unit': ['Units'],
##                        'BotanicalGardenUnit': ['Unit'],


##                        'SourceInstitutionID': ['Unit'],
##                        'SourceID': ['Unit'],
##                        'UnitID': ['Unit'],
##                        'DateLastEdited': ['Unit'],
##                        'Identifications': ['Unit'],
##                            'Identification': ['Identifications'],
##                                'Result': ['Identification'],
##                                    'TaxonIdentified': ['Result'],
##                                        'HigherTaxa': ['TaxonIdentified'],
##                                            'HigherTaxon': ['HigherTaxa'],
##                                                'HigherTaxonName': ['HigherTaxon'],
##                                                'HigherTaxonRank': ['HigherTaxon'],
##                                        'ScientificName': ['TaxonIdentified'],
##                                            'FullScientificNameString': ['ScientificName'],
##                                            'NameAtomised': ['ScientificName'],
##                                                'Botanical': ['NameAtomised'],
##                                                    'GenusOrMonomial': ['Botanical'],
##                                                    'FirstEpithet': ['Botanical'],
##                                                    'AuthorTeam': ['Botanical'],
##                                        'InformalNameString': ['TaxonIdentified'],
##                        'Notes': ['Unit']

##                            }


