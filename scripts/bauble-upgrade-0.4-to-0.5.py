#!/usr/bin/env python

#what has changed?
#------------------
#Accession.date added (done, dates set to 3000-01-01)
#Accession.source_type - is not an EnumCol, shouldn't be any problems 
#except that any 'NoneType' string should be changed to None (done)
#Accession.prov_type - change '<not set>' to None (done)
#Accession.wild_prov_status - change '<not set>' to None (done)
#Donor.donor_type - change '<not set>' to None (done)
#Plant.acc_type - change '<not set>' to None (done)
#Plant.acc_status - change '<not set>' to None (done)
#PlantHistory - though this table didn't exist so there is nothing
#to migrate
# remove Collector.collector2 (done)

# can i alter tables in the database or only work on dumped text files
# maybe taked dumped text files, create a temporary sqlite database 
# in memory and then dump new database files

import os, re, glob, shutil

OUT_PATH = 'new'

if not os.path.exists(OUT_PATH):
    os.mkdir('new')

def open_outfile(filename):
    out_filename = '%s%s%s' % (OUT_PATH, os.sep, filename)
#    if os.path.exists(out_filename):
#        response =raw_input('%s exists. You you want to overwrite it? (y/n): '\
#                            % out_filename)
#        if response in ('n', 'N'):        
#            sys.exit(1)
    return open(out_filename, 'w')            


def build_line_regex(columns):
    rx_str = ""
    for c in columns:
        rx_str += '(?P<%s>(?P<%s_quote>")?.*?(?(%s_quote)")),' %  (c,c,c)
    rx_str = rx_str[:-1] + '$' # replace the last comma with the EOL marker
    return re.compile(rx_str)


def build_line_template(columns):
    '''
    build the template string from columns for outputing the lines
    '''
    s = ''
    for column in columns:
        s += '%%(%s)s,' % column
    return s[:-1] + '\n'

def migrate_accession(filename):
    
    # TODO: what about date column, is it required, i.e, not None, if so
    # then we may need to put fake dates in 1900-01-01
    columns = ("id","acc_id","prov_type","notes","wild_prov_status",
               "source_type","speciesID")
    rx = build_line_regex(columns)
    outfile = open_outfile(filename)
    new_columns = columns + ('date',)
    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
    line_template = build_line_template(new_columns)
    for line in open(filename).readlines()[1:]:
        line = line.strip()
        m = rx.match(line).groupdict()
        new_line = m.copy()
        if m['source_type'] == '"NoneType"':
            #new_line['source_type'] = None
            new_line['source_type'] = ''
        if m['prov_type'] == '"<not set>"':
            #new_line['prov_type'] = None
            new_line['prov_type'] = ''
        if m['wild_prov_status'] == '"<not set>"':
            #new_line['wild_prov_status'] = None
            new_line['wild_prov_status'] = ''
        new_line['date'] = '1900-01-01'
        new_out_line = line_template % new_line
        outfile.write(line_template % new_line)


def migrate_donor(filename):
    columns = ("id","fax","tel","name","donor_type","address","email")
    rx = build_line_regex(columns)
    outfile = open_outfile(filename)
    outfile.write(str(columns)[1:-1].replace("'", '"').replace(' ', ''))
    line_template = build_line_template(columns)
    for line in open(filename).readlines()[1:]:
        line = line.strip()
        m = rx.match(line).groupdict()
        new_line = m.copy()
        if m['donor_type'] == '"NoneType"':
            new_line['donor_type'] = None
        outfile.write(line_template % new_line)
        
        
def migrate_plant(filename):
    columns = ("id","accessionID","plant_id","notes","acc_type","locationID",
               "acc_status")
    rx = build_line_regex(columns)
    outfile = open_outfile(filename)
    outfile.write(str(columns)[1:-1].replace("'", '"').replace(' ', ''))
    line_template = build_line_template(columns)
    for line in open(filename).readlines()[1:]:
        line = line.strip()
        m = rx.match(line).groupdict()
        new_line = m.copy()
        if m['acc_type'] == '"<not set>"':
            new_line['acc_type'] = None
        if m['acc_status'] == '"<not set>"':
            new_line['acc_status'] = None
        outfile.write(line_template % new_line)
    
    
def migrate_collection(filename):
    columns = ("id","accessionID","countryID","elevation","habitat",
               "collector2","locale","notes","longitude","latitude","geo_accy",
               "elevation_accy","coll_date","coll_id","collector")
    rx = build_line_regex(columns)
    outfile = open_outfile(filename)
    new_columns = columns[0:5] + columns[6:]
    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', ''))
    line_template = build_line_template(new_columns)
    for line in open(filename).readlines()[1:]:
        line = line.strip()
        m = rx.match(line).groupdict()
        new_line = m.copy()
        collector2 = new_line.pop('collector2')[1:-1]
        if collector2 != '':        
            new_line['notes'] = '%s, removed %s from the collector2 field' % \
                                (new_line['notes'], collector2)
        outfile.write(line_template % new_line)

            
def test():            
    '''
    test output data is correct
    '''
    pass

migration_map = {'Accession.txt': migrate_accession,
                 'Collection.txt': migrate_collection,
                 'Plant.txt': migrate_plant,
                 'Donor.txt': migrate_donor,
                 }

print 'migrating...'
for f in glob.glob("*.txt"):
    print f
    if f in migration_map:
        migration_map[f](f)
    else:
        shutil.copyfile(f, '%s%s%s' % (OUT_PATH, os.sep, f))
        

