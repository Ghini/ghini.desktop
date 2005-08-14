#
# garden plugin 
#

import os, sys
from accession import *
from bauble.plugins import BaublePlugin
from accession import Accession
from location import Location
from plant import Plant
from reference import Reference
from source import Donor, Donation, Collection

class GardenPlugin(BaublePlugin):
#    def editors(self):
#        return None
#        return [AccessionEditor, LocationEditor, PlantEditor, ReferenceEditor,
#                 DonorEditor, SourceEditor]
    tables = [Accession, Location, Plant, Reference, Donor, Donation, Collection]
    
    def create_tables(cls):
        super(GardenPlugin, cls).create_tables()    
    create_tables = classmethod(create_tables)
#    def tables(self):
#        return [Accession, Location, Plant, Reference, Donor, Donation, Collection]
    depends = ("PlantsPlugin","GeographyPlugin")

plugin = GardenPlugin