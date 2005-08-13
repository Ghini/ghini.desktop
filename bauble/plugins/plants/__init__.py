
#from accession import *
#from cultivation import *

# TODO: there is going to be problem with the accessions MultipleJoin
# in plantnames, plants should really have to depend on garden unless
# plants is contained within garden, but what about herbaria, they would
# also need to depend on plants, what we could do is have another class
# with the same name as the other table that defines new columns/joins
# for that class or probably not add new columns but add new joins 
# dynamically

# TODO: should create the table the first time this plugin is loaded, if a new 
# database is created there should be a way to recreate everything from scratch

from bauble.plugins import BaublePlugin
from family import Family
from genus import Genus
from plantname import Plantname


class PlantsPlugin(BaublePlugin):
    tables = (Family, Genus, Plantname)
    
    def install(self):
        """
        do any setup and configuration required bt this plugin like
        creating tables, etc...
        """
        # TODO: this requires the imex.csv plugin module
        for t in tables:
            t.createTable()
            
        
        csv = plugins.tools.imex_csv.CSVImporter(None)
        #csv = iecsv.CSVImporter(None)
        # TODO: need to fix this path business, should have some sort
        # of install ini file that tells us where to find the data directory
        #path = utils.get_main_dir() + ".." + os.sep + 'data' + os.sep
        path = os.dirname(__file__ + os.sep + 'default')
        #path = '/home/brett/devel/bauble/data/'
        print path
        files = ['Family.txt']
        csv.start([path+os.sep+f for f in files])
        
plugin = PlantsPlugin
