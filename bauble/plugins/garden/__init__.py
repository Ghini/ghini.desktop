#
# garden plugin 
#

import os, sys
from accession import *
from bauble.plugins import BaublePlugin, tables
from accession import Accession
from location import Location
from plant import Plant
from reference import Reference
from source import Donor, Donation, Collection

class GardenPlugin(BaublePlugin):

#    editors = [AccessionEditor, LocationEditor, PlantEditor, ReferenceEditor,
#               DonorEditor, SourceEditor]
    tables = [Accession, Location, Plant, Reference, Donor, Donation, Collection]
    
    def create_tables(cls):
        super(GardenPlugin, cls).create_tables()    
        # TODO: how do we know the order that the tables are going to be created
        # somehow we need to sort the plugins/tables/whatever so that those
        # that depend on another table are created last, actually i don't think
        # it matters on the order since this is being done on the meta class
        # of the table
        # add joins to tables from plants
        acc_join = MultipleJoin('Accessions', joinColumn='plantname_id')
        tables["Plantname"].sqlmeta.addJoin(acc_join)
    create_tables = classmethod(create_tables)
    
    depends = ("PlantsPlugin","GeographyPlugin")

plugin = GardenPlugin