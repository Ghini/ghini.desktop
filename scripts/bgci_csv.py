#!/usr/bin/env python
#
# bgci_csv.py
#
# print a CSV formatted string to stdout that conforms to the BGCI CSV
# importer
#

# TODO: this shares alot of code with createdb, we could probably
# create file to hold all the common db code


import sys, os
from optparse import OptionParser
from getpass import getpass

usage = 'usage: %prog [options] dbname'
parser = OptionParser(usage)
parser.add_option('-H', '--host', dest='hostname', metavar='HOST',
                  help='the host to connect to')
parser.add_option('-u', '--user', dest='user', metavar='USER',
                  help='the user name to use when connecting to the server')
parser.add_option('-P', '--port', dest='port', metavar='PORT',
                  help='the port on the server to connect to')
# TODO: should be able to pass in a password as well, maybe if
# options.password is None then we can ask
parser.add_option('-p', action='store_true', default=False, dest='password',
                  help='ask for a password')
parser.add_option('-d', '--dbtype', dest='dbtype', metavar='TYPE',
                  help='the database type')
parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
                  default=False, help='verbose output')

options, args = parser.parse_args()
try:
    dbname =  args[-1]
except:
    parser.error('You must specify a database name')

if not options.user:
    options.user = os.environ['USER']

dbapi = None
if options.dbtype == 'postgresql':
    dbapi = __import__('psycopg2')
else:
    parser.error('You must specify the database type with -d')

# build connect() args and connect to the server
connect_args = ['dbname=%s' % dbname]
if options.hostname is not None:
    connect_args.append('host=%s' % options.hostname)
if options.password:
    password = getpass('Password for %s: ' % options.user)
    connect_args.append('password=%s' % password)
if options.user:
    connect_args.append('user=%s' % options.user)
if options.port:
    connect_args.append('port=%s' % options.port)

conn_str = ' '.join(connect_args)
if options.verbose:
    print(conn_str)
conn = dbapi.connect(conn_str)
cursor = conn.cursor()

sql = "select distinct g.hybrid, g.genus, s.sp_hybrid, s.sp, s.infrasp_rank, s.infrasp from genus as g, species as s, accession as a, plant as p where s.genus_id = g.id and a.species_id = s.id and p.accession_id = a.id and p.acc_status='Living accession' and s.sp != 'sp' and s.sp != 'spp' and s.sp != 'sp.' and s.sp != 'spp.' order by g.genus, s.sp;"

if options.verbose:
    print(('- %s' % sql))

cursor.execute(sql)
rows = cursor.fetchall()
GENUS_HYBRID_COL = 0
GENUS_COL = 1
SP_INFRA_RANK_COL = 5
for row in rows:
    line = list(row)
    # change infrasp_rank and infrasp to a cultivate if infrasp_rank=='cv.'
    if line[SP_INFRA_RANK_COL] == 'cv.':
        line[SP_INFRA_RANK_COL] = None
        line.append(line[SP_INFRASP])
    else:
        line.append(None)
    print((','.join(['%s' % (col or '') for col in line])))

if options.verbose:
    print(('%s results' % cursor.rowcount))

if options.verbose:
    print('** Warning: the output from this file is not suitable for '\
          'importing into the BGCI Plant Search when the verbose output (-v) '\
          'option is enabled.')

def main():
    pass

if __name__ == "__main__":
    main()
