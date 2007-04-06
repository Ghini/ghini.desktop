#
# postgres.py
#
# Description: handle importing and exporting data into a postgres database
# using Postgres' native import commands
#

# TODO: get the data from an XML export and use and XSL transform to transform
# the data into a format that Postgres understands

# TODO: on import we need to determine the type of the data or it need to be
# explicitly set so we know if we need to transform the XML, or what the CSV
# delimeters are or if its just a straight dump that needs to be imported

#COPY command. copy zip_codes from '/path/to/csv/ZIP_CODES.txt' DELIMITERS ',' CSV;
