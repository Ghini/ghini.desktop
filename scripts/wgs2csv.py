#!/usr/bin/env python
import os, sys, csv, re

files = ['tblLevel1.txt', 'tblLevel2.txt', 'tblLevel3.txt', 'tblLevel4.txt',
         'tblGazetteer.txt']

# TODO: i don't think this is necessary
#class UnicodeCSVReader:
#    
#    def build_rx(self, filename):
#        self.file = open(filename)
#        line = self.file.readline()
#        line = line.strip()
#        rx_str = '^'
#        for col in [c.replace(' ', '_') for c in line.split(self.delimiter)]:
#            rx_str += '(?P<%s>.*?)[%s]{1}' % (col, self.delimiter)
#        #rx_str = rx_str[:-1] + '$'
#        rx_str = rx_str[:-6] + '$'
#        print rx_str
#        self.rx = re.compile(rx_str, re.UNICODE)
#
#    def __init__(self, filename, delimiter=','):
#        self.delimiter = delimiter
#        self.build_rx(filename)
#            
#    def __iter__(self):
#        return self
#    
#    def next(self):
#        line = self.file.readline().strip()
#        if line == '':
#            raise StopIteration
#        m = self.rx.match(line)
#        if m is None:
#            return None            
#        return m.groupdict()

def get_data(filename, id_name):
    data = {}
    reader = csv.DictReader(open(filename), delimiter='*')
    #reader = UnicodeCSVReader(filename, delimiter='*')
    for line in reader:
        #print line
        data[line[id_name]] = line
    return data



level_one_data = get_data('tblLevel1.txt', 'L1 code')
level_two_data = get_data('tblLevel2.txt', 'L2 code')
level_three_data = get_data('tblLevel3.txt', 'L3 code')
level_four_data = get_data('tblLevel4.txt', 'L4 code')
gazetteer_data = get_data('tblGazetteer.txt', 'ID')

date = ['id', 'level', 'parent_id', 'name']
id = 1
for l1_code in level_one_data:
    print '1 - %s' % level_one_data[l1_code]['L1 continent']
    for l2 in [l2 for l2 in level_two_data.values() if l2['L1 code'] == l1_code]:
        print '  2 -- %s' % l2['L2 region']
        for l3 in [l3 for l3 in level_three_data.values() if l3['L2 code'] == l2['L2 code']]:
            print '    3 -- %s' % l3['L3 area']
            for l4 in [l4 for l4 in level_four_data.values() if l4['L3 code'] == l3['L3 code']]:
                if l3['L3 area'] != l4['L4 country']:
                    print '        4 -- %s' % l4['L4 country']
                for gaz in [gaz for gaz in gazetteer_data.values() if gaz['L4 code'] == l4['L4 code']]:
                    print '         G -- %s' % gaz['Gazetteer']

            #for l4_code in level_four_data:                
#                for key, line in gazetteer_data.iteritems():
#        if line['L1 code'] == l1_code:
#            print line['Gazetteer']
