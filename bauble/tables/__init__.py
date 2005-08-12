#
# tables module
#

# TODO: create a MetaSomething class that hold information about
# the tables such as the default editor, default children for the expansions
# of the search, and anything else that would keep me from checking 
# the type of each table and doing something according to the type, would
# also be a good idea to automatically load any changes to the meta from the
# the Preferences
 
# TODO: change the module level tables variable to be a list so that
# a module can provide more than one table, what about table creation?,
# editors?, should the tables be looked up in the _tables dict by name
# or module name, module name would probably be better and this a list
# of table could be provided by the table or maybe another dict that
# is keyed by module name one keyed by table name that gives the module
# it belongs to

# TODO: other tables to consider
# Collections
# Cultivation
# Images
#  - uri
#  - plantname_id
# a table that can hold uri to keys, i.e. Stephen Brewers Palm Key

# TODO: it would probably be good to make a table class that inherits
# from SQLObject that all of my tables inherit from, then we could
# do global changes from one place, though i don't know if this
# would screw up the metaclass thing

# TODO: the values dict for a column should be able to contain
# a table column and the values looked up from the table, although
# really if the values are coming from a table then maybe sticking
# with a join is better database design

# TODO: should sanitize the modules a bit, if a table depends directly
# on another table then it should be in the same module or the one module
# should depend on another if the table could be shared against multiple 
# modules
# for example a "plants" module could hold information about plants
# while a "botanic gardens" module could hold all information about collection
# but "botanic gardens" is dependent on plants
# also provide a geography module which most modules would be dependent
# on, e.g. if there was an "animal" module
# these modules could also provide both tables and editors instead
# of having seperate modules for each while the __init__.py could
# just provide the list of editors, table and dependents and hints
# to other modules, e.g. the search map for the view.search module
# of course this means we would have to abandon the editors/table/views
# layout and just have a plugins folder and each plugin contains
# everything it needs or else list another plugins it depends on, the 
# problem then is that animals and plants shouldn't share the same
# images table but each should have it's own copy of images table, this 
# would 
# things to consider with this approach:
#    1. would have to be more careful about table name clashes, e.g
#    if you had the plants module and the animals module then they 
#    couldn't both provide and images table, unless we set the nameing
#    to automatically append a prefix to each table
#    2. 

import os, os.path
import re
from sqlobject import *
from sqlobject.inheritance import *

# all tables should inherit from BaubleTable
#class BaubleTable(InheritableSQLObject):
print '********** importing tables'
class BaubleTable(SQLObject):    
    sqlmeta.cacheValues = False
    
    def __init__(self, **kw):
        super(BaubleTable, self).__init__(**kw)
        self.values = {}
        

class _tables(dict):
    
    def __init__(self):
        path, name = os.path.split(__file__)
        modules = []
        if path.find("library.zip") != -1: # using py2exe
            pkg = "tables"
            zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
            x = [zipfiles[file][0] for file in zipfiles.keys() if pkg in file]
            s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
            rx = re.compile(s.encode('string_escape'))
            for filename in x:
                m = rx.match(filename)
                if m is not None:
                    modules.append('%s.%s' % (pkg, m.group(1)))                    
        else:
            for d in os.listdir(path):
                full = path + os.sep + d 
                if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                    modules.append("tables." + d)
                    
        for m in modules:
            print "importing " + m
            m = __import__(m, globals(), locals(), ['tables'])
            if hasattr(m, 'tables'):
                for t in m.tables:
                    self[t.__name__] = t    


    def __getattr__(self, attr):
        if not self.has_key(attr):
            return None
        return self[attr]


def create_tables():
    """
    create all the tables
    """
    for t in tables.values():
        t.createTable()
    
    
tables = _tables()
        
