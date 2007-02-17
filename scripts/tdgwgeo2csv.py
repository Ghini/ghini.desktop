#!/usr/bin/env python
#
# fix_geotdwg.py
#
# Description: convert TDWG plant distribution files out of the box to a single
# CSV file 
#
# NOTE: the only pre processing that has to be done to the files
# is to convert them to UTF-8, for some reason i have problems trying to
# convert from ISO-8859-1, probably b/c i don't completely understand unicode
#

# TODO: should create new id's for each entry and have a tdwg_code for each
# so we can maintain as much data as possbible

import os, sys, re, codecs
import csv

# l1 - Continent, tblLevel1.txt, UTF-8
# l2 - Region, tblLevel2.txt, UTF-8
# l3 - BotanicalCountry, tblLevel4, ISO-8859-15
# l4 - BaseUnit, tblLevel4.txt, ISO-8859-15
# gazette (places), tblGazette.txt, ISO-8859-15

cwd, _dummy = os.path.split(__file__)
src_dir = os.path.join(cwd, os.pardir, "data", "tdwg-geo")
out_dir = os.path.join(cwd, os.pardir, "data", "tdwg-geo")

class Reader:
    def __init__(self, filename, encoding='utf8'):
        self.file = codecs.open(filename, "r", encoding)
        self.headers = self.file.next().strip().split('*')
        s = ""
        for h in self.headers:
            h2 = h.replace(' ', '_')
            s += '(?P<%s>.*?)\*' % h2
        s = s[:-2] + '$'#        print s
        self.line_rx = re.compile(s)
        
        
    def group(self, line):    
        m = self.line_rx.match(line.strip())
        if m is None:            
            raise ValueError("could not match:\n%s\n%s" % \
                (unicode(line), (unicode(s))))
        return m.groupdict()


    def __iter__(self):
        return self

    
    def next(self):
        line = self.file.next()
        # remove the stupid ,00 decimals at the end of the integers
        #line = self.file.next().replace(',00','')        
        return self.group(line)            


#L1 code*L1 continent
level1_col_map = {"L1 code": "code",# continents
                  "L1 continent": "continent"}
# L2 code*L2 region*L1 code*L2 ISOcode
level2_col_map = {"L2 code": "code", #regions
                  "L2 region": "region",
                  "L1 code": "Continent",
                  "L2 ISOcode": "iso_code"} # should really remove this col
#L3 code*L3 area*L2 code*L3 ISOcode*Ed2status*Notes                  
level3_col_map = {"L3 code": "code",  # botanical country
                  "L3 area": "name",
                  "L2 code": "Region",
                  "L3 ISOcode": "iso_code",
                  "Ed2status": "ed2_status",
                  "Notes": "notes"}
#L4 code*L4 country*L3 code*L4 ISOcode*Ed2status*Notes                  
level4_col_map = {"L4 code": "code", # basic unit
                  "L4 country": "name",
                  "L3 code": "BotanicalCountry",
                  "L4 ISOcode": "iso_code",
                  "Ed2status": "ed2_status",
                  "Notes": "notes"}
#ID*Gazetteer*L1 code*L2 code*L3 code*L4 code*Kew region code*Kew region subdivision*Kew region*Synonym*Notes
gazette_col_map = {"ID": "code",
                   "Gazetteer": "place",
                   "L1 code": "Continent",
                   "L2 code": "Region",
                   "L3 code": "BotanicalCountry",
                   "L4 code": "BasicUnit",
                   "Kew region code": "kew_regionID",
                   "Kew region subdivision": "kew_subdiv_code",
                   "Kew region": "kew_region", 
                   "Synonym": "synonym",
                   "Notes": "notes"
                  }
            
## # data dictionaries
## continent = {}
## region = {}
## botanical_country = {}
## basic_unit = {}
## place = {}      

## metas = [Meta("Continent", "tblLevel1.txt", "utf8", level1_col_map),
##          Meta("Region", "tblLevel2.txt", "utf8", level2_col_map),
##          Meta("BotanicalCountry", "tblLevel3.txt", "iso-8859-15",
##               level3_col_map),
##          Meta("BasicUnit", "tblLevel4.txt", "iso-8859-15", level4_col_map),
##          Meta("Place", "tblGazetteer.txt","iso-8859-15", gazette_col_map),
##         ]
              
## data_map = {"Continent": continent,
##             "Region": region,
##             "BotanicalCountry": botanical_country,
##             "BasicUnit": basic_unit,
##             "Place": place}

## def write_file(table, dict):
##     """
##     dict should be a dictionary whose keys are the id's of the table
##     and values are dicts of row values
##     """
##     f = open(table_map[table] + '.txt', 'wb')
##     keys = dict.values()[1].keys()
##     header = str(keys)[1:-1].replace("'", '"').replace(' ', '') + '\n'
##     f.write(header)
##     writer = csv.DictWriter(f, keys, quoting=csv.QUOTE_NONNUMERIC)
##     writer.writerows(dict.values())


def kew_key(line):
    return line['kew_region_code'] + line['kew_subdiv']

table_to_id_map = {"Continent": "continentID",
            "Region": "regionID",
            "BotanicalCountry": "botanical_countryID",
            "BasicUnit": "basic_unitID",
            "Place": "placeID"}

## def replace_id_names(values):
##     new = []
##     for v in values:
##         if v in table_to_id_map:
##             new.append(table_to_id_map[v])
##         else:
##             new.append(v)
##     return new
        

#
# replace table code column with id's
#
## def reduce(line):
##     for key, value in line.iteritems():
##         if key in table_to_id_map:
##             code = line.pop(key)
##             if code in data_map[key]:
##                 foreign_id = data_map[key][code]["id"]            
##                 line[table_to_id_map[key]] = foreign_id
##             else:
##                 line[table_to_id_map[key]] = ""
##     return line
    
## def reduce_place(line):
##     line.pop("kew_regionID")
##     line.pop("kew_region")
##     line.pop("kew_subdiv_code")
##     return line
    

## def quote(s, encoding='utf8'):
##     if isinstance(s, int):
##         return str(s)
##     else:        
##         if isinstance(s, unicode):
##             return '"%s"' % s.encode(encoding)
##         else:
##             return '"%s"' % s
#        re
#        return unicode(s)
#        print s
#        obj = codecs.encode(s)
#        print obj
#        return obj
#        return unicode('"%s"' % s, encoding)

    
## def write_list(outfile, values):    
##     outfile.write(','.join(map(quote, values)) + '\n')


## def write_dict(outfile, dic, order):
##     s = ""
##     #','.join(map(quote, values)) + '\n'
##     for header in order:
##         s += quote(dic[header]) + ','
##     s = s[:-1] # remove last comma
##     outfile.write(s + '\n')
    
    
## def write_data(filename, data):
##     outfile = codecs.open(filename, "w", 'utf8')
##     headers = data[0].keys()
##     write_list(outfile, headers)
##     for line in data:
##         write_dict(outfile, line, headers)


# converted rows organized by tdwg_code so we can resolve parents
converted_rows = {}
id_ctr = 1

class Row(dict):

    def __init__(self, id=None, name=None, tdwg_code=None, iso_code=None,
                 parent_id=None):
        super(Row, self).__init__(id=id, name=name, tdwg_code=tdwg_code,
                                  iso_code=iso_code, parent_id=parent_id)

    columns = ['id', 'name', 'tdwg_code', 'iso_code', 'parent_id']

    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            return getattr(self, item)

    def __setattr__(self, key, value):
        self[key] = value

    def csv(self):
        s = []
        for c in self.columns:
            if self[c] is None:
                #s.append('None')
                s.append('')
            elif c is 'id' or c is 'parent_id':
                s.append(self[c])
            else:
                s.append('"%s"' % self[c].encode('utf8'))
#                s.append(quote(self[c]))
        return ','.join(s)

def convert_level1():
    global converted_data, id_ctr
    reader = Reader(os.path.join(src_dir, 'tblLevel1.txt'), 'utf8')
    for line in reader:
        r = Row(id=str(id_ctr), name=line['L1_continent'],
                tdwg_code=line['L1_code'])
        converted_rows[line['L1_code']] = r
        id_ctr+=1


def convert_level2():
    global converted_data, id_ctr
    reader = Reader(os.path.join(src_dir, 'tblLevel2.txt'), 'utf8')
    for line in reader:
        r = Row(id=str(id_ctr), name=line['L2_region'],
                tdwg_code=line['L2_code'], iso_code=line['L2_ISOcode'])
        r.parent_id = converted_rows[line['L1_code']]['id']
        converted_rows[line['L2_code']] = r
        id_ctr+=1

        
def convert_level3():
    global converted_data, id_ctr    
    reader = Reader(os.path.join(src_dir, 'tblLevel3.txt'), 'iso-8859-15')
    for line in reader:
        r = Row(id=str(id_ctr), name=line['L3_area'],
                tdwg_code=line['L3_code'], iso_code=line['L3_ISOcode'])
        #r.parent_id = converted_rows[line['L2_code']]['id']
        r['parent_id'] = converted_rows[line['L2_code']]['id']
        converted_rows[line['L3_code']] = r
        id_ctr+=1


def convert_level4():
    global converted_data, id_ctr    
    reader = Reader(os.path.join(src_dir, 'tblLevel4.txt'), 'iso-8859-15')
    for line in reader:
        r = Row(id=str(id_ctr), name=line['L4_country'],
                tdwg_code=line['L4_code'], iso_code=line['L4_ISOcode'])
        r.parent_id = converted_rows[line['L3_code']]['id']
        converted_rows[line['L4_code']] = r
        id_ctr+=1


def convert_gazetteer():
    global converted_data, id_ctr    
    reader = Reader(os.path.join(src_dir, 'tblGazetteer.txt'), 'iso-8859-15')
    for line in reader:
        # TODO: create two rows, one for the gazetteer data and one for the
        # kew data
        r = Row(id=str(id_ctr), name=line['Gazetteer'],
                tdwg_code=line['ID'])

        # throw out anything that doesn't have a name, there seems
        # to be at least one row that doesn't have a name and is really just
        # a place holder for a kew region
        if line['Synonym'] != '':
            print '%s == %s' % (line['Gazetteer'].encode('utf8'), line['Synonym'].encode('utf8'))
        if r.name == '' or line['Synonym'] != '':
            continue
        try:
            r.parent_id = converted_rows[line['L4_code']]['id']
        except KeyError, e:
            try:
                r.parent_id = converted_rows[line['L3_code']]['id']
            except KeyError, e:
                try:
                    r.parent_id = converted_rows[line['L2_code']]['id']
                except KeyError, e:
                    try:
                        r.parent_id = converted_rows[line['L1_code']]['id']
                    except KeyError, e:
                        pass

        # throw out anyting from the gazetteer that doesn't have a parent
        if r.parent_id is not None:
            converted_rows[line['ID']] = r
            id_ctr+=1
              

def main():
    global id_ctr, converted_rows
    convert_level1()
    convert_level2()
    convert_level3()
    convert_level4()
    convert_gazetteer()

    print ','.join(['"%s"' % c for c in Row.columns])
    for r in converted_rows.values():
#        if r.name == '':
#            print '***** %s *******' % r
        print r.csv()

    print Row(id='%s' % id_ctr, name='Cultivated').csv()
    id_ctr +=1 

#    for r in converted_rows.values():           
#        if r.parent_id is None:
#            print r

#    codes = converted_rows.keys()
#    l = 0
#    for c in converted_rows.keys():
#        if len(c) > l:
#            l = len(c)
#    print 'max: %s' % l
        

##     for meta in metas:        
##         print meta.filename + ' --> ' + meta.table
##         reader = Reader(os.path.join(src_dir, meta.filename), meta)
##         data = data_map[meta.table]
##         for line in reader:
##             if meta.table == "Place":
##                 line = reduce_place(line)
##             line = reduce(line)                        
##             line["id"] = id
##             data[line['code']] = line
##             id_ctr += 1            
##         write_data(out_dir + meta.table + ".txt", data.values())
##     print "Done."
                        

if __name__ == "__main__":
    main()
    
#    # read in all of level1
#    id = 1
#    reader = csv.DictReader(open(infiles['level1']))
#    l1_dict = {}
#    for line in reader:
#        line['id'] = id
#        l1_dict[line['code']] = line
#        id += 1
#    
#    # read in all of level2 and insert level1 id
#    id = 1
#    reader = csv.DictReader(open(infiles['level2']))
#    l2_dict = {}
#    for line in reader:
#        line['id'] = id
#        line['continentID'] = l1_dict[line['level1_code']]['id']
#        del line['level1_code']
#        l2_dict[line['code']] = line
#        id += 1
#        #print line
#        
#    # read level 3 and insert level2 id
#    id = 1
#    reader = csv.DictReader(open(infiles['level3']))
#    l3_dict = {}
#    for line in reader:
#        line['id'] = id
#        line['regionID'] = l2_dict[line['level2_code']]['id']
#        del line['level2_code']
#        l3_dict[line['code']] = line
#        id += 1
#        #print line
#    
#    # read level 4 and insert level 3 id
#    id = 1
#    reader = csv.DictReader(open(infiles['level4']))
#    l4_dict = {}
#    for line in reader:
#        line['id'] = id
#        line['areaID'] = l3_dict[line['level3_code']]['id']
#        del line['level3_code']
#        l4_dict[line['code']] = line
#        id += 1
#
#        
#    # read in gazette and replace codes with id's
#    id = 1
#    reader = csv.DictReader(open(infiles['gaz']))
#    kew_dict = {}
#    kew_id = 1
#    gaz_dict = {}
#    for line in reader:
#        if not kew_dict.has_key(line['kew_region_code'] + line['kew_subdiv']):
#            kd = {}
#            kd['id'] = kew_id
#            kd['code'] = line['kew_region_code']
#            kd['region'] = line['kew_region']
#            kd['subdiv'] = line['kew_subdiv']
#            kew_id += 1
#            kew_dict[kew_key(line)] = kd
#
#        line['kew_regionID'] = kew_dict[kew_key(line)]['id']
#        
#        del line['kew_region_code']
#        del line['kew_region']
#        del line['kew_subdiv']
#        
#        line['id'] = id
#        if line['l4_code'] != '':
#            line['stateID'] = l4_dict[line['l4_code']]['id']
#        else: line['stateID'] = None
#        
#        if line['l3_code'] != '':
#            line['areaID'] = l3_dict[line['l3_code']]['id']
#        else: line['areaID'] = None
#        
#        if line['l2_code'] != '':
#            line['regionID'] = l2_dict[line['l2_code']]['id']
#        else: line['regionID'] = None
#        
#        del line['l1_code']
#        del line['l2_code']
#        del line['l3_code']
#        del line['l4_code']
#        gaz_dict[line['id']] = line
#        id += 1
#        
#        
#    write_file('level1', l1_dict)
#    write_file('level2', l2_dict)
#    write_file('level3', l3_dict)
#    write_file('level4', l4_dict)
#    write_file('gaz', gaz_dict)
#    write_file('kew', kew_dict)
