#!/usr/bin/env python
#
# tdwggeo2csv.py
#
# Description: convert TDWG plant distribution files out of the box to a single
# CSV file
#

# TODO: should create new id's for each entry and have a tdwg_code for
# each so we can maintain as much data as possbible

# TODO: we should probably include the original text files in bauble
# and run the conversion script on build

# TODO: add a notes column to geography so we carry over the extra
# geography data(kew regions, notes, etc.) and so that we can add
# notes to them in bauble

import codecs
import os
import re
from optparse import OptionParser

# l1 - Continent, tblLevel1.txt, UTF-8
# l2 - Region, tblLevel2.txt, UTF-8
# l3 - BotanicalCountry, tblLevel4, ISO-8859-15
# l4 - BaseUnit, tblLevel4.txt, ISO-8859-15
# gazette (places), tblGazette.txt, ISO-8859-15

parser = OptionParser()
parser.add_option('-d', '--directory', dest='directory',
                  help='directory of WGS txt files', metavar='DIR')

(options, args) = parser.parse_args()
if not options.directory:
    parser.error('directory required')

cwd, _dummy = os.path.split(__file__)
src_dir = options.directory

class Reader(object):

    def __init__(self, filename, encoding='utf8'):
        self.file = codecs.open(filename, "r", encoding)
        self.headers = self.file.next().strip().split('*')
        s = ""
        # sanitize the column headers
        for h in self.headers:
            h2 = h.replace(' ', '_')
            s += '(?P<%s>.*?)\*' % h2
        s = s[:-2] + '$'#        print s
        self.line_rx = re.compile(s)


    def group(self, line):
        m = self.line_rx.match(line.strip())
        if m is None:
            raise ValueError("could not match:\n%s\n%s" % \
                (str(line), (str(s))))
        return m.groupdict()


    def __iter__(self):
        return self


    def __next__(self):
        line = next(self.file)
        # remove the stupid ,00 decimals at the end of the integers
        #line = self.file.next().replace(',00','')
        return self.group(line)



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
        print((r.csv()))
        id_ctr+=1


def convert_level2():
    global converted_data, id_ctr
    reader = Reader(os.path.join(src_dir, 'tblLevel2.txt'), 'utf8')
    for line in reader:
        r = Row(id=str(id_ctr), name=line['L2_region'],
                tdwg_code=line['L2_code'], iso_code=line['L2_ISOcode'])
        r.parent_id = converted_rows[line['L1_code']]['id']
        converted_rows[line['L2_code']] = r
        print((r.csv()))
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
        print((r.csv()))
        id_ctr+=1


def convert_level4():
    global converted_data, id_ctr
    reader = Reader(os.path.join(src_dir, 'tblLevel4.txt'), 'iso-8859-15')
    for line in reader:
        # skip redundant lines from level 3
        if line['L4_code'].endswith('-OO'):
            continue
        r = Row(id=str(id_ctr), name=line['L4_country'],
                tdwg_code=line['L4_code'], iso_code=line['L4_ISOcode'])
        r.parent_id = converted_rows[line['L3_code']]['id']
        converted_rows[line['L4_code']] = r
        print((r.csv()))
        id_ctr+=1


def convert_gazetteer():
    global converted_data, id_ctr
    reader = Reader(os.path.join(src_dir, 'tblGazetteer.txt'), 'iso-8859-15')
    for line in reader:
        # try to only include those things that are unique to the gazeteer
        if line['L3_code'] in converted_rows and \
                converted_rows[line['L3_code']]['name'] == line['Gazetteer']:
            continue
        elif line['L4_code'] in converted_rows and \
                converted_rows[line['L4_code']]['name'] == line['Gazetteer']:
            continue

        # TODO: create two rows, one for the gazetteer data and one for the
        # kew data
        r = Row(id=str(id_ctr), name=line['Gazetteer'],
                tdwg_code=line['ID'])

        # throw out anything that doesn't have a name, there seems
        # to be at least one row that doesn't have a name and is really just
        # a place holder for a kew region
        if line['Synonym'] != '':
            #print '%s == %s' % (line['Gazetteer'].encode('utf8'), line['Synonym'].encode('utf8'))
            pass
        if r.name == '' or line['Synonym'] != '':
            continue
        try:
            r.parent_id = converted_rows[line['L4_code']]['id']
        except KeyError as e:
            try:
                r.parent_id = converted_rows[line['L3_code']]['id']
            except KeyError as e:
                try:
                    r.parent_id = converted_rows[line['L2_code']]['id']
                except KeyError as e:
                    try:
                        r.parent_id = converted_rows[line['L1_code']]['id']
                    except KeyError as e:
                        pass

        # add the converted rows and print out the csv line
        converted_rows[line['ID']] = r
        print((r.csv()))
        id_ctr+=1


def main():
    global id_ctr, converted_rows

    print((','.join(['"%s"' % c for c in Row.columns])))
    convert_level1()
    convert_level2()
    convert_level3()
    convert_level4()
    convert_gazetteer()

    print((Row(id='%s' % id_ctr, name='Cultivated').csv()))
    id_ctr +=1



if __name__ == "__main__":
    main()

