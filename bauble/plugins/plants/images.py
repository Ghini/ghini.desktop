# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#
# Images table definition
#

#from bauble.plugins import BaubleTable, tables
#from bauble.treevieweditor import TreeViewEditorDialog
#
#
#class Image(BaubleTable):
#
#    # not unique but if a duplicate uri is entered the user
#    # should be asked if this is what they want
#    uri = StringCol()
#    label = StringCol(length=50, default=None)
#
#    # copyright ?
#    # owner ?
#
#    # should accessions also have a images in case an accession
#    # differs from a plant slightly or should it just have a different
#    # species
#    #plant = MultipleJoin("Plantnames", joinColumn="image_id")
#    species = ForeignKey('Species', cascade=True)
#
#
#    def __str__(self): return self.label
#
##
## Image editor
##
#class ImageEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.image.columns"
#    column_width_pref = "editor.image.column_width"
#    default_visible_list = ['label', 'uri', 'species']
#
#    label = 'Images'
#
#    def __init__(self, parent=None, select=None, defaults={}):
#
#        TreeViewEditorDialog.__init__(self, tables["Image"],
#                                            "Image Editor", parent,
#                                            select=select, defaults=defaults)
#        titles={"uri": "Location (URL)",
#                 "label": "Label",
#                 'speciesID': 'Plant Name'}
#        self.columns.titles = titles
