#
# dump table schemas
#

# i'm not actually sure what this does

tables = get_all_tables() # return {name: sqlobject,...}
for table_name, table in tables.iteritems():
    f = file(path + os.sep + table_name, "w")
    for row in table.select():
        values = []
        values.append(row.id)
        for col in table._columns:
            if type(col) == ForeignKey:
                name = col.name + "ID"
            else: name = col.name
            values.append(getattr(row, name))
        f.write(str(values)[1:-1]+"\n")
    f.close()
        