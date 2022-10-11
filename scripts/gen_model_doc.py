#!/usr/bin/env python

# TODO: use pydoc to get documentation from tables

# TODO: the generated document provides alot of information but
# doesn't really explain what it is

# TODO: cross reference ColumnProperty properties from the mappers
# back to the Table definitions, if for each of the tables or columns
# we generate an anchor tag of the form <a name="tablename_colname">
# then it should be easy enough to generate the links in the mapper
# section

import os, sys
import xml.sax.saxutils as saxutils
sys.path.append('.')
import sqlalchemy as sa
from sqlalchemy.orm import *
from sqlalchemy.orm.mapper import _mapper_registry
from sqlalchemy.orm.properties import *

import bauble
import bauble.db as db
import bauble.pluginmgr as pluginmgr
from bauble.prefs import prefs
import bauble.view as view

uri = 'sqlite:///:memory:'
db.open(uri, verify=False)
prefs.init()
pluginmgr.load()
db.create(False)
pluginmgr.init(True)

def column_type_str(col):
    print((type(col)))
    if isinstance(col, sa.String):
        return 'string'
    elif isinstance(col, sa.Unicode):
        return 'unicode'
    elif isinstance(col, sa.Integer):
        return 'integer'
    elif isinstance(col, sa.ForeignKey):
        return 'foreign key(int)'


html_head = '''<html><head>
<style>
.table{
padding-bottom: 10px;
}
h1{
background-color: #778899;
color: white;
padding-left: 5px;
}

.details{
margin-left: 10px;
}
</style>
</head><body>'''

html_tail='''</body>
</html>'''

table_template = '''<div class="table"><h2 class="name">%(table_name)s</h2>
<div class="details">
%(columns)s
</div>
</div>'''

columns_template = '''<h3>Columns</h3>
<ul>%s</ul>'''

column_template = '''<li>%s</li>'''

joins_template = '''<h3>Joins</h3>
<ul>%s</ul>'''
join_template = '''<li>%s</li>'''

print(html_head)

classes = {}
for strategy in view.SearchView.search_strategies:
    if not isinstance(strategy, view.MapperSearch):
        continue
    domains = strategy._domains
    for domain, detail in list(domains.items()):
        dom, c = classes.setdefault(detail[0], ([], detail[1]))
        dom.append(domain)
    for cls, data in list(classes.items()):
        mapper = class_mapper(cls)
        print(('<h1>%s</h1>' % mapper.local_table.name))
        domains, cols = data
        print(('<p>search domain(s): %s</p>' % ', '.join(domains)))
        print(('<p>default search column(s): %s</p>' % ', '.join(cols)))

        print('<h2>Columns</h2>')
        print('<ul>')
        for column in mapper.c:
            if not column.name in ('_last_updated', '_created'):
                print(('<li>%s</li>' % column.name))
        print('</ul>')

        print('<h2>Relations</h2>')
        print('<ul>')
        for prop in mapper.iterate_properties:
            if isinstance(prop, ColumnProperty):
                continue
            if prop.uselist:
                print(('<li>%s: list of %s</li>' %  (prop.key, prop.target.name)))
            else:
                print(('<li>%s: a %s</li>' %  (prop.key, prop.target.name)))
        print('</ul>')

print(html_tail)
import sys
sys.exit(1)
print(html_head)

print('<h1>Tables</h1>')
for table in sorted(db.metadata.table_iterator(), key=lambda x: x.name):
    columns_str = ''
    for col in table.columns:
        s = '<b>%s</b>: %s' % (col.name, col.type)
        if len(col.foreign_keys) > 0:
            s += ', ForeignKey(%s)' % \
                ', '.join(['%s.%s' % (f.column.table, f.column.name) for f in col.foreign_keys])
        if not col.nullable:
            s += ' [required]'
        columns_str += column_template % s

    if columns_str != '':
        columns_markup = columns_template % columns_str

    print((table_template % ({'table_name': table.name,
			     'columns': columns_markup})))
#                             'properties': properties_markup})
#			     'joins': joins_markup})


print('<br/><hr/><br/>')
print('<h1>Mappers</h1>')
for mapper in sorted(_mapper_registry, key=lambda x: x.class_.__name__):

    # this str builder copied from the Mapper class
    #s = mapper.class_.__name__ + "->" + (mapper.entity_name is not None and "/%s" % mapper.entity_name or "") + (mapper.local_table and mapper.local_table.description or str(mapper.local_table)) + (mapper.non_primary and "|non-primary" or "")
    s = mapper.class_.__name__ + "->" + (mapper.local_table.name is not None and "/%s" % mapper.local_table.name or "") + (mapper.local_table and mapper.local_table.description or str(mapper.local_table)) + (mapper.non_primary and "|non-primary" or "")
    print(('<h2 class="name">%s</h2>' % s))
    print('<div class="details">')
    print('<h3>Properties</h3>')
    props_str = ''
    for p in sorted(mapper.iterate_properties,
                    key=lambda x: isinstance(x, ColumnProperty)):
        if isinstance(p, ColumnProperty):
            props_str += '<li>%s</li>' % [str(c) for c in p.columns]
        else:
            props_str += '<li>%s</li>' % saxutils.escape(str(p))
    if props_str is not '':
        print(('<ul>%s</ul>' % props_str))
    print('</div>')

print(html_tail)
