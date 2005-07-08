#!/usr/bin/env python

import os, sys
import csv

base_dir = os.pardir + os.sep + os.pardir + os.sep + "data" + os.sep + \
           "old" + os.sep

infiles = {'gaz': base_dir + 'geo_gazetteer.txt',
         'level1': base_dir + 'geo_level1.txt',
         'level2': base_dir + 'geo_level2.txt',
         'level3': base_dir + 'geo_level3.txt',
         'level4': base_dir + 'geo_level4.txt'}

#infiles = {'gaz': '../../data/geo_gazetteer.txt',
#         'level1': '../../data/geo_level1.txt',
#         'level2': '../../data/geo_level2.txt',
#         'level3': '../../data/geo_level3.txt',
#         'level4': '../../data/geo_level4.txt'}

outdir = 'out'

table_map = {'gaz': 'Places',
             'level1': 'Continents',
             'level2': 'Regions',
             'level3': 'Areas',
             'level4': 'States',
             'kew': 'KewRegions'}

def write_file(table, dict):
    f = open(table_map[table] + '.txt', 'wb')
    keys = dict.values()[0].keys()
    header = str(keys)[1:-1].replace("'", '"').replace(' ', '') + '\n'
    f.write(header)
    writer = csv.DictWriter(f, keys, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerows(dict.values())


def kew_key(line):
    return line['kew_region_code'] + line['kew_subdiv']

if __name__ == "__main__":
    
    # read in all of level1
    id = 0
    reader = csv.DictReader(open(infiles['level1']))
    l1_dict = {}
    for line in reader:
        line['id'] = id
        l1_dict[line['code']] = line
        id += 1
    
    # read in all of level2 and insert level1 id
    id = 0
    reader = csv.DictReader(open(infiles['level2']))
    l2_dict = {}
    for line in reader:
        line['id'] = id
        line['continentID'] = l1_dict[line['level1_code']]['id']
        del line['level1_code']
        l2_dict[line['code']] = line
        id += 1
        #print line
        
    # read level 3 and insert level2 id
    id = 0
    reader = csv.DictReader(open(infiles['level3']))
    l3_dict = {}
    for line in reader:
        line['id'] = id
        line['regionID'] = l2_dict[line['level2_code']]['id']
        del line['level2_code']
        l3_dict[line['code']] = line
        id += 1
        #print line
    
    # read level 4 and insert level 3 id
    id = 0
    reader = csv.DictReader(open(infiles['level4']))
    l4_dict = {}
    for line in reader:
        line['id'] = id
        line['areaID'] = l3_dict[line['level3_code']]['id']
        del line['level3_code']
        l4_dict[line['code']] = line
        id += 1
        #print line
        
    # read in gazette and replace codes with id's
    id = 0
    reader = csv.DictReader(open(infiles['gaz']))
    kew_dict = {}
    kew_id = 0
    gaz_dict = {}
    for line in reader:
        
        #if not kew_dict.has_key(line['kew_region_code'] + line['kew_subdiv']):
        if not kew_dict.has_key(kew_key(line)) and line[kew_region_code] is not '':
            kd = {}
            kd['id'] = kew_id
            kd['code'] = line['kew_region_code']
            kd['region'] = line['kew_region']
            kd['subdiv'] = line['kew_subdiv']
            kew_id += 1
            kew_dict[kew_key(line)] = kd

        line['kew_regionID'] = kew_dict[kew_key(line)]['id']
        
        del line['kew_region_code']
        del line['kew_region']
        del line['kew_subdiv']
        
        line['id'] = id
        if line['l4_code'] != '':
            line['countryID'] = l4_dict[line['l4_code']]['id']
        else: line['countryID'] = None
        
        if line['l3_code'] != '':
            line['areaID'] = l3_dict[line['l3_code']]['id']
        else: line['areaID'] = None
        
        if line['l2_code'] != '':
            line['regionID'] = l2_dict[line['l2_code']]['id']
        else: line['regionID'] = None
        
        del line['l1_code']
        del line['l2_code']
        del line['l3_code']
        del line['l4_code']
        gaz_dict[line['id']] = line
        id += 1
        
        
    write_file('level1', l1_dict)
    write_file('level2', l2_dict)
    write_file('level3', l3_dict)
    write_file('level4', l4_dict)
    write_file('gaz', gaz_dict)
    write_file('kew', kew_dict)
