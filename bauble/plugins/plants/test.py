# 
# need to create a test for all possible species strings
# 

# TODO: should also test that when we delete everything from an entry that
# the value is set as None in the database instead of as an empty string

import os
from sqlobject import *
import bauble
from bauble.plugins import plugins, tables


print 
print __file__
uri = 'sqlite:///os.path.dirname(__file__)/test.sqlite'
sqlhub.processConnection = connectionForURI(uri)    
sqlhub.processConnection.getConnection()
sqlhub.processConnection = sqlhub.processConnection.transaction()    

bauble.plugins.load()

Family = tables['Family']
Genus = tables['Genus']
Species = tables['Species']

values = {'family': 'TestFamily',
          'genus': 'TestGenus'}



def set_up():
    f = Family(values['family'])
    g = Genus(values['genus'])
    
def tear_down():
    f.destroySelf()
    g.destroySelf()
    
def test():    
    # insert genus
    # insert species
    # insert sp_author
    # ... etc ...
    # ok.clicked()
    # test the committed species has the same value in the database as we
    # put in the entries
    pass

set_up()
test()
tear_down()
