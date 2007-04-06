#
# sqlite.py
#
# Description: handle importing and exporting data into a SQLite database using
# SQLite native import commands
#

# TODO: get the data from an XML export and use and XSL transform to transform
# the data into a format that SQLite understands

# use .separator, .import

def import_csv(connection, filename, table, delimiter=','):
    '''
    '''
    # CRAP: this isn't supported from 3.0 onward
    connection.execute('COPY %s FROM %s USING DELIMITERS %s' % \
                       (table.name, filename, delimiter))
