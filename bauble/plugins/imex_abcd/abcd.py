#
# abcd.py
# 
# module for read and writing Access to Biological Collection 
# Data (ABCD) files
#

import string
from string import Template
from bauble.utils.log import log, debug

main_template_str = """<?xml version="1.0"?>
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
                                $family
                                $scientific_name
                                $informal_names
                                $distribution
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
    <nameatomised>
        <botanical>
            <genusormonomial>$genus</genusormonomial>
            <firstepithet>$sp</firstepithet>
        </botanical>
    </nameatomised>
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
    
    
def plants_to_abcd(plants):
    """
    convert a list of plants/clones instances to an abcd record
    """
    abcd = None
    units = []
    for p in plants:
        acc = p.accession
        id = string.strip(str(acc.acc_id) + '.' + str(p.plant_id))
        f = family_template.substitute(family=acc.species.genus.family)
        n = name_template.substitute(genus=acc.species.genus, sp=acc.species.sp)
        #informal_name = informal_name_template.substitute(informal_name=acc.species.vernac_name or "")
        informal_name = informal_name_template.substitute(informal_name=
            acc.species.default_vernacular_name or "")
        #d = distribution_template.substitute(distribution=acc.species.distribution or "")
        if acc.species.species_meta is not None:
            dist = acc.species.species_meta.distribution or ''
        else: dist = ''
        d = distribution_template.substitute(distribution=dist)
        #d = distribution_template.substitute(distribution=
        #    acc.species.plant_meta.distribution or "")
        units.append(unit_template.substitute(unitid=id, family=f, 
                                              scientific_name=n, 
                                              informal_names=informal_name,
                                              distribution=d))
    
    abcd = main_template.substitute(units='\n'.join(units))
    #debug(abcd)
    return abcd