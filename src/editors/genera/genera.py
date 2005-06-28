#
# genera.py
#

import gtk

import editors
from tables import tables

# TODO: should be able to pass possible_values for a column
# for things like the hybrid column which can only be certain values
# and maybe some sort of flag about adding new values if not in the list
# or restricting the user only to those values in possible_values,
# if restricted the column should be a combobox, if you can add other
# values then a comboboxentry would be better
class GeneraEditor(editors.TreeViewEditorDialog):

    visible_columns_pref = "editor.genera.columns"
    column_width_pref = "editor.genera.column_width"
    
    def __init__(self, parent=None, select=None, defaults={}):

        self.sqlobj = tables.Genera

        self.column_data = editors.createColumnMetaFromTable(self.sqlobj)

        # set headers
        headers = {'genus': 'Genus',
                   'author': 'Author',
                   'hybrid': 'Hybrid',
                   'family': 'Family'}
        self.column_data.set_headers(headers)

        # TODO: maybe a function would be better then we could pass
        # a list which would define both the order and the visibility
        # set default visible
        self.column_data["family"].visible = True
        self.column_data["genus"].visible = True

        # set visible according to stored prefs
        self.set_visible_columns_from_prefs(self.visible_columns_pref)

        editors.TreeViewEditorDialog.__init__(self, "Genera Editor", parent,
                                              select=select, defaults=defaults)
        


    def get_completions(self, text, colname):
        maxlen = -1
        model = None
        if colname == "family":
            model = gtk.ListStore(str, int)
            if len(text) > 2:
                sr = tables.Families.select("family LIKE '"+text+"%'")
                for row in sr:
                    model.append([str(row), row.id])
        return model, maxlen # not setting maxlen but maybe we should