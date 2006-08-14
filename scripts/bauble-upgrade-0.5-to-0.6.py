#!/usr/bin/env python

# How to use this scripts to upgrade your version of Bauble from 
# 0.5.x to 0.6.x
# 1. connect to existing database with version 0.5.x of Bauble
# 2. from the Bauble menu select Tools\Export\Comma Separated Values
# 3. selected a directory to create the backup files
# 4. from the command line cd to the directory where the backup files are
# 5. run this script, the converted files are in the new/ directory
# 6. connect to the new database with Bauble 0.5.x
# 7. from the Bauble menu select File\New
# 8. from the Bauble menu select Tools\Import\Comma Separated Values
# 9. select all the files from the new/ directory, click OK
# 10. check that the values in the database are correct

# what has changed ?
# ------------------
# lower case import files
# Accession.acc_id is now Accession.code
# Plant.plant_id is now Plant.code
# change 1/1/190(0/1) dates and any other temporary dates to None
# make sure appropriate columns are unicode
# if col.endswith('ID') 
#    col= '%s' % ([col:-2], '_id')


# can i alter tables in the database or only work on dumped text files
# maybe taked dumped text files, create a temporary sqlite database 
# in memory and then dump new database files

import os, re, glob, shutil

OUT_PATH = 'new'

if not os.path.exists(OUT_PATH):
    os.mkdir('new')


camel_rx = re.compile('([A-Z])')
def camel_to_underscore(filename):    
    def replace(m):
        return '_%s' % m.group(0).lower()    
    return '%s%s' % (filename[0].lower(), camel_rx.sub(replace, filename[1:]))


def open_outfile(filename):
    out_filename = '%s%s%s' % (OUT_PATH, os.sep, filename)
#    if os.path.exists(out_filename):
#        response =raw_input('%s exists. You you want to overwrite it? (y/n): '\
#                            % out_filename)
#        if response in ('n', 'N'):        
#            sys.exit(1)
    return open(out_filename, 'w')            


def build_line_regex(columns, **kwargs):
    rx_str = "^"
    for c in columns:
        if c in kwargs:
            rx_str += kwargs[c]
        else:
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


def migrate_donation(filename):    
    columns = ['id','date','accession_id','notes','donor_acc','donor_id']
    rx = build_line_regex(columns)
    outfile = open_outfile(camel_to_underscore(filename))
    outfile.write(str(columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
    line_template = build_line_template(columns)
    for line in open(filename).readlines()[1:]:
        line = line.strip()
        m = rx.match(line)
        new_line = m.groupdict().copy()
        if new_line['date'] in ('1901-01-01', '1901-12-13'):
            new_line['date'] = ''    
        outfile.write(line_template % new_line)
        
        
def migrate_plant(filename):
    columns = ["id","accession_id","plant_id","notes","acc_type","location_id",
               "acc_status"]
    rx = build_line_regex(columns)
    outfile = open_outfile(camel_to_underscore(filename))
    new_columns = ["id","accession_id","code","notes","acc_type","location_id",
                   "acc_status"]
    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
    line_template = build_line_template(new_columns)
    for line in open(filename).readlines()[1:]:
        line = line.strip()
        m = rx.match(line)
        new_line = m.groupdict().copy()
        new_line['code'] = new_line.pop('plant_id')
        outfile.write(line_template % new_line)


def migrate_accession(filename):    
    columns = ("id","acc_id","prov_type","notes","wild_prov_status",
               "source_type","date","species_id")
    rx = build_line_regex(columns)
    outfile = open_outfile(camel_to_underscore(filename))
    new_columns = ("id","code","prov_type","notes","wild_prov_status",
                   "source_type","date","species_id")    
    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
    line_template = build_line_template(new_columns)
    for line in open(filename).readlines()[1:]:
        line = line.strip()
        m = rx.match(line)
        new_line = m.groupdict().copy()
        new_line['code'] = new_line.pop('acc_id')
        if new_line['date'] in ('1901-01-01', '1901-12-13'):
            new_line['date'] = ''
        # TODO: check the source_type is either 'Donation' or 'Collection'
        outfile.write(line_template % new_line)


def migrate_collection(filename):
    # TODO: should check for bad dates but we don't have any collections with 
    # dates so i won't bother
    pass 


#def migrate_donor(filename):
#    columns = ["id","fax","tel","name","donor_type","address","email"]
#    rx = build_line_regex(columns)
#    outfile = open_outfile(filename)
#    outfile.write(str(columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
#    line_template = build_line_template(columns)
#    for line in open(filename).readlines()[1:]:
#        line = line.strip()
#        m = rx.match(line).groupdict()
#        new_line = m.copy()
#        if m['donor_type'] == '"NoneType"':
#            new_line['donor_type'] = ''
#        outfile.write(line_template % new_line)
        
        
#def migrate_plant(filename):
#    columns = ("id","accessionID","plant_id","notes","acc_type","locationID",
#               "acc_status")
#    rx = build_line_regex(columns)
#    outfile = open_outfile(filename)
#    outfile.write(str(columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
#    line_template = build_line_template(columns)
#    for line in open(filename).readlines()[1:]:
#        line = line.strip()
#        m = rx.match(line).groupdict()
#        new_line = m.copy()
#        if m['acc_type'] == '"<not set>"':
#            new_line['acc_type'] = ''
#        if m['acc_status'] == '"<not set>"':
#            new_line['acc_status'] = ''
#        outfile.write(line_template % new_line)
#    
#    
#def migrate_donation(filename):
#    columns = ["id","accessionID","notes","donor_acc","donorID"]
#    rx = build_line_regex(columns)
#    outfile = open_outfile(filename)    
#    new_columns = columns + ['date']
#    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
#    line_template = build_line_template(new_columns)
#    for line in open(filename).readlines()[1:]:
#        line = line.strip()
#        m = rx.match(line).groupdict()    
#        new_line = m.copy()        
#        new_line['date'] = '1900-01-01'
#        outfile.write(line_template % new_line)
#    
#    
#def migrate_family(filename):
#    columns = ["id","notes","family"]
#    rx = build_line_regex(columns)
#    outfile = open_outfile(filename)    
#    new_columns = columns + ['qualifier']
#    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
#    line_template = build_line_template(new_columns)
#    for line in open(filename).readlines()[1:]:
#        line = line.strip()
#        m = rx.match(line).groupdict()
#        new_line = m.copy()        
#        new_line['qualifier'] = '""'
#        outfile.write(line_template % new_line)
#        
#        
#def migrate_genus(filename):
#    columns = ["id","familyID","notes","genus","hybrid","author"]
#    rx = build_line_regex(columns)
#    outfile = open_outfile(filename)    
#    new_columns = columns + ['qualifier']
#    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
#    line_template = build_line_template(new_columns)
#    for line in open(filename).readlines()[1:]:
#        line = line.strip()
#        m = rx.match(line).groupdict()
#        new_line = m.copy()        
#        new_line['qualifier'] = '""'
#        outfile.write(line_template % new_line)
#        
#        
#def migrate_species(filename):
#    columns = ["id","sp","default_vernacular_nameID","notes","isp","id_qual",
#               "sp_author","isp_rank","isp_author","genusID","cv_group",
#               "sp_qual","sp_hybrid"]
#    rx = build_line_regex(columns)
#    outfile = open_outfile(filename)    
#    new_columns = columns + ['infrasp', 'infrasp_rank', 'infrasp_author']
#    new_columns.remove('isp')
#    new_columns.remove('isp_rank')
#    new_columns.remove('isp_author')
#    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
#    line_template = build_line_template(new_columns)
#    for line in open(filename).readlines()[1:]:
#        line = line.strip()
#        m = rx.match(line).groupdict()
#        new_line = m.copy()        
#        new_line['infrasp'] = new_line.pop('isp')
#        new_line['infrasp_rank'] = new_line.pop('isp_rank')
#        new_line['infrasp_author'] = new_line.pop('isp_author')
#        outfile.write(line_template % new_line)
#        
#        
#def migrate_collection(filename):
#    columns = ("id","accessionID","countryID","elevation","habitat",
#               "collector2","locale","notes","longitude","latitude","geo_accy",
#               "elevation_accy","coll_date","coll_id","collector")
#    rx = build_line_regex(columns)
#    outfile = open_outfile(filename)
#    new_columns = columns[0:5] + columns[6:]
#    outfile.write(str(new_columns)[1:-1].replace("'", '"').replace(' ', '')+'\n')
#    line_template = build_line_template(new_columns)
#    for line in open(filename).readlines()[1:]:
#        line = line.strip()
#        m = rx.match(line).groupdict()
#        new_line = m.copy()
#        collector2 = new_line.pop('collector2')[1:-1]
#        if collector2 != '':        
#            new_line['notes'] = '%s, removed %s from the collector2 field' % \
#                                (new_line['notes'], collector2)
#        outfile.write(line_template % new_line)

            
def test():            
    '''
    test output data is correct
    '''
    pass


migration_map = {'Accession.txt': migrate_accession,
                 'Donation.txt': migrate_donation,
                 'Plant.txt': migrate_plant
                 }

print 'migrating...'
for f in glob.glob("*.txt"):
    print '%s -> %s' % (f, camel_to_underscore(f))
    if f in migration_map:
        migration_map[f](f)
    else:
       shutil.copyfile(f, '%s%s%s' % (OUT_PATH, os.sep, camel_to_underscore(f)))
        

