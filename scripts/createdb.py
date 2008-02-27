#!/usr/bin/env python

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
parser.add_option('-o', '--owner', dest='owner', metavar='OWNER',
		  help='the owner of the newly created database')
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

#commands = ['create']
#if cmd not in commands:
#    parser.error('%s is an invalid command' % cmd)

def get_owner():
    if options.owner:
	return options.owner
    else:
	return raw_input('Database Owner: ')

def build_postgres_command():
    pass

def build_mysql_command():
    pass

dbapi = None
if options.dbtype == 'postgres':
    dbapi = __import__('psycopg2')
elif options.dbtype == 'mysql':
#    dbapi = __import__('MySQLdb')
    parser.error('At the moment this script only support postgres '\
		 'database types')
else:
    parser.error('You must specify the database type with -d')

if not options.owner:
    options.owner = os.environ['USER']

# build connect() args and connect to the server
connect_args = ['dbname=postgres']
if options.hostname is not None:
    connect_args.append('host=%s' % options.hostname)
if options.password:
    password = getpass('Password for %s: ' % options.user)
    connect_args.append('password=%s' % password)
if options.user:
    connect_args.append('user=%s' % options.user)
if options.port:
    connect_args.append('port=%s' % options.port)

conn = dbapi.connect(' '.join(connect_args))
# ISOLATION_LEVEL_AUTOCOMMIT needed from create database
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT) 
cursor = conn.cursor()

# check if the database already exists
sql = "SELECT datname FROM pg_database WHERE datname='%s';" % dbname
if options.verbose:
    print '- %s' % sql
cursor.execute(sql)
rows = cursor.fetchall()
if (dbname,) in rows:
    print 'database %s already exists' % dbname
    sys.exit(1)

# create the user if the user doesn't already exist
sql = "SELECT rolname FROM pg_roles WHERE rolname='%s';" % options.owner
if options.verbose:
    print '- %s' % sql
cursor.execute(sql)
rows = cursor.fetchall()
if (options.owner,) in rows:
    print 'user %s already exist' % options.owner
else:
    password = getpass('Password for new database owner %s: ' % options.owner)
    sql = "CREATE ROLE %s LOGIN PASSWORD '%s';" % (options.owner, password)
    if options.verbose:
	print '- %s' % sql
    cursor.execute(sql)
    conn.commit()

# create the database and give owner permissions to alter it
options_dict = dict(dbname=dbname, owner=options.owner)
sql = 'CREATE DATABASE %(dbname)s OWNER %(owner)s' % options_dict
if options.verbose:
    print '- %s' % sql
cursor.execute(sql)
conn.close()
