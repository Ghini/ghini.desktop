#
# abcd.py
# 
# modules for read and writing Access to Biological Collection Data (ABCD) files
#

from string import Template

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
        id = str(acc.acc_id) + '.' + str(p.plant_id)        
        f = family_template.substitute(family=acc.plantname.genus.family)
        n = name_template.substitute(genus=acc.plantname.genus, sp=acc.plantname.sp)
        units.append(unit_template.substitute(unitid=id, family=f, scientific_name=n))
    
    abcd = main_template.substitute(units='\n'.join(units))
    return abcd