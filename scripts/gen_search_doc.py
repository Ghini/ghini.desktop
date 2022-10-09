# generate documentation about searching
# - the list of domains and their relevant tables
# - link to the model doc for the columns to use or combine the two

# TODO: at the moment this scripts only searches all the plugins
# modules for classes that subclass bauble.BaubleMapper and then
# generates the documents from the mappers...we need to combine this
# with the domains from the search strategies

# TODO: generate docs in a common wiki syntax, either in
# reStructuredText, markdown or wikidot format

"""
Generate docs about search strategies, mapper properties, etc.
"""

import os, sys

if 'PYTHONPATH' in os.environ:
    sys.path.insert(0, os.environ['PYTHONPATH'])

import sqlalchemy as sa

import bauble
import bauble.pluginmgr as pluginmgr
from bauble.prefs import prefs
import bauble.paths as paths

uri = 'sqlite:///:memory:'
bauble.open_database(uri, verify=False)
prefs.init()
pluginmgr.load()
bauble.create_database(False)
pluginmgr.init()
session = bauble.Session()

path = os.path.join(paths.lib_dir(), 'plugins')
modules = pluginmgr._find_module_names(path)
classes = set()
for mod in modules:
    fullname = 'bauble.plugins.%s' % mod
    mod = __import__(fullname, globals(), locals(), [fullname])
    for item in dir(mod):
        item = getattr(mod, item)
        try:
            if issubclass(item, bauble.BaubleMapper):
                if item not in classes:
                    classes.add(item)
        except:
            pass



from sqlalchemy.orm.properties import PropertyLoader, ColumnProperty

for item in classes:
    mapper = sa.orm.class_mapper(item)
    columns = []
    collections = []
    for p in mapper.iterate_properties:
        if isinstance(p, ColumnProperty):
            columns.append(p)
        elif isinstance(p, PropertyLoader):
            collections.append(p)
        else:
            raise Exception('**Error')
        #s = '-- %s' % p.key

    print(('%s (%s table)' % (item.__name__ , mapper.local_table.name)))
    print(' * Columns:')
    for c in columns:
        print(('  |- %s' % c.key))
    print(' * Collections:')
    for c in collections:
        print(('  |- %s (collection of %s)'  % (c.key, c.mapper.class_.__name__)))
    print('')
