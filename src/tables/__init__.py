#
# tables module
#

# TODO: create a MetaSomething class that hold information about
# the tables such as the default editor, default children for the expansions
# of the search, and anything else that would keep me from checking 
# the type of each table and doing something according to the type, would
# also be a good idea to automatically load any changes to the meta from the
# the Preferences
# 


import os, os.path

from sqlobject import *

class _tables(dict):
    
    def __init__(self):
        path, name = os.path.split(__file__)
        for d in os.listdir(path):
            full = path + os.sep + d 
            if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                m = __import__("tables." + d, globals(), locals(), ['tables'])                
                self[m.table.name] = m.table
            
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
        
