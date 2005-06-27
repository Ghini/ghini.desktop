#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


import os, sys
import utils

if sys.platform == "win32":
    sys.path.append(utils.get_main_dir() + os.sep + "lib" + os.sep + "win32")
    os.environ["PATH"] += utils.get_main_dir() + os.pathsep + "lib" + os.sep + "win32"
sys.path.append(utils.get_main_dir() + os.sep + "lib")
os.environ["PATH"] += utils.get_main_dir() + os.pathsep + "lib"
    
# i guess we would need to use the builtin tk library to show an
# error if gtk is not available, but that adds extra dependencies
# for py2exe

import pygtk
if not utils.main_is_frozen():
    pygtk.require("2.0")
import gtk

try:
    from sqlobject import *
except ImportError:
    msg = "SQLObject not installed. Please install SQLObject from http://www.sqlobject.org"
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)


import app
import prefs
bauble = app.baubleApp
prefs = prefs.Preferences

if __name__ == "__main__":
    gtk.threads_init() # initialize threading
    bauble.main()
