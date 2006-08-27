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

# TODO: also need ability to dump to darwin core, should consider just writing
# an xsl transformation to do the conversion instead of writing more export
# code, Darwin Core is a flat structure and from i understand doesn't have a 
# sense of "unit"

# TODO: need to also respect the number of children and element can have
# e.g. Units can have 1 to infinity Unit children whereas elements require
# at least one and some can have at most one child

class SQLObjectToABCD:
    def __init__(so_class, parent):
	pass

    def toABCD():
	pass


# temporary placeholder until lxml
class Element: 
    def __init__(tag):
	Element.__init__(self, tag)

# temporary placeholder
class SubElement: 
    def __init__(parent, tag):
	SubElement.__init__(self, parent, tag)


# it would be good if this could somehow incapsulate more than one tag but 
# still stick to the element tree api so we could easily read and write the 
# data
class SpeciesToABCD(SubElement):
    def __init__(self, species, parent):
	pass
    
    def markup(self):
	'''
	<scientificname>
	<fullscientificnamestring>
	$name
	</fullscientificnamestring>
	</scientificname'''
	return str(species)
	

class AccessionABCD:
    def __init__(so_class, parent):
	assert isinstance(parent, SpeciesABCD)


class DataSets(Element):
    def __init__(self):
	# assert list of classes that can be children of ABCDRoot
	# [DataSet]
	Element.__init__(self, "DataSets")

	def append(child):
	    assert isinstance(child, DataSet)

class DataSet(SubElement):

    def __init__(parent):
	assert isinstance(parent [DataSets])
	# possible children [DataSetGUID, TechnicalContacts, ContentContacts, 
	# OtherProviders, Metadata, Units]


class Units(SubElement):
    def __init__(self, parent):
	assert isinstance(parent, [DataSet])

    def append(self, child):
	# assert [Unit]
	pass


class Unit:
    def append(self, child):
	# assert [UnitGUID, SourceInstitutionID, SourceID, UnitID, 
	# UnitIDNumeric, LastEditor, DateLastEdited, Owner, IPRStatements, 
	# UnitContentContacts, SourceReference, UnitReferences, 
	# Identifications, RecordBasis, KindOfUnit, SpecimenUnit, 
	# ObservationUnit, CultureCollectionUnit, MycologicalUnit, 
	# HerbariumUnit, BotanicalGardenUnit, PlantGeneticResourceUnit, 
	# ZoologicalUnit, PaleontologicalUnit, MultiMediaObjects, 
	# Associations, Assemblages, NamedCollectionsOrSurvey, Gathering, 
	# CollectorsFieldNumber, MeasurementsOrFacts, Sex, Age, Sequences, 
	# Notes, RecordURI, EAnnotations, UnitExtension
	pass

#datasets = ABCDDataSets()
#ds = ABCDDataSet(datasets)
#units = ABCDUnits(ds)
#unit = ABCDUnit(units)
#print datasets

main_template_str = """<?xml version="1.0" encoding="utf-8"?>
<datasets xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:noNamespaceSchemaLocation="file:/home/brett/devel/ABCD/ABCD.xsd">
    <dataset>
        <units>
            $units
        </units>
    </dataset>
</datasets>
"""
main_template = Template(main_template_str)

unit_template_str = """
           <unit>
                <unitid>$unitid</unitid>
                <identifications>
                    <identification>
                    <result>
                        <taxonidentified>
                           <scientificname>
                             $family
                             $scientific_name
                             $informal_names
                             $distribution
                           </scientificname>
                         </taxonidentified>
                    </result>
                 </identification>
                </identifications>
            </unit>
"""
unit_template = Template(unit_template_str)


family_template_str = """
<highertaxa>
    <highertaxon>
        <highertaxonrank>familia</highertaxonrank>
        <highertaxonname>$family</highertaxonname>
     </highertaxon>                                    
</highertaxa>
"""
family_template = Template(family_template_str)


name_template_str = """
<scientificname>
  <fullscientificnamestring>
    $name
  </fullscientificnamestring>
</scientificname>
"""
name_template = Template(name_template_str)


# ***********
# TODO: this is not a standard in ABCD but we need it to create the labels
# if we could just return this abcd data instead of writing a file then 
# we could add
distribution_template_str = """
<distribution>
$distribution
</distribution>
"""
distribution_template = Template(distribution_template_str)


#
# i'm using informal name here for the vernacular name
#
informal_name_str = """
<informalnamestring>
$informal_name
</informalnamestring>
"""
informal_name_template = Template(informal_name_str)




def accessions_to_abcd(accessions):
    """
    convert a list of accessions instance to an abcd record
    """
    plants = []
    # get a list of all plants and pass to plants_to_abcd
    for a in accessions:
        for p in a.plants:
            plants.append(p)
    return plants_to_abcd(plants)
    
def xml_safe(ustr):    
    return xml.sax.saxutils.escape(ustr).encode('utf-8')


def plants_to_abcd(plants):
    """
    convert a list of plants/clones instances to an abcd record
    """
    abcd = None
    units = []
    for p in plants:
        acc = p.accession
        #id = string.strip(unicode(acc.acc_id) + '.' + str(p.plant_id))
        # TODO: what if someone doesn't want to use '.' to separate 
        # acc_id and plant_id
        id = xml_safe(acc.code + '.' + p.code)
        
        f = family_template.substitute(family=xml_safe(str(acc.species.genus.family)))
        n = name_template.substitute(name=xml_safe(str(acc.species)))
        v = acc.species.default_vernacular_name or ""
        informal_name = informal_name_template.substitute(informal_name=
                                                          xml_safe(str(v)))
        
        if acc.species.species_meta:
            d = acc.species.species_meta.distribution or ""
        else:
            d = ""
        dist = distribution_template.substitute(distribution=xml_safe(str(d)))
        
        units.append(unit_template.substitute(unitid=id, family=f, 
                                              scientific_name=n, 
                                              informal_names=informal_name,
                                              distribution=dist))
    
    #abcd = xml.sax.saxutils.escape(main_template.substitute(units='\n'.join(units))).encode('utf-8')
    abcd = main_template.substitute(units='\n'.join(units))
    #debug(abcd)
    return abcd
