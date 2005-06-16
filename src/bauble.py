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

import os, os.path, sys
import utils

# is this the best way to add lib to the load path???
path, name = os.path.split(__file__)
sys.path.append(path + os.sep + "lib")

# i guess we would need to use the builtin tk library to print an
# error if gtk is not available
import pygtk
pygtk.require("2.0")
import gtk

try:
    from sqlobject import *
except ImportError:
    msg = "SQLObject not installed. Please install SQLObject from http://www.sqlobject.org"
    utils.message_dialog(msg, gtk.MESSAGE_ERROR)

from gui import *
from conn_mgr import *
import tables
import prefs
from prefs import Preferences


DEBUG_SQL = False

#
# Bauble
#                    
class Bauble:
    
    
    def __init__(self):
        # keep the directory where this resides for loading local files
        self.path, dummy = os.path.split(__file__)

        # open default database on startup
        self.conn = None
        num_tries = 0
        default_conn = Preferences[prefs.conn_default_pref]
        while self.conn is None:
            cm = ConnectionManagerDialog(default_conn)
            r = cm.run()
            if r == gtk.RESPONSE_CANCEL or r == gtk.RESPONSE_CLOSE or \
               r == gtk.RESPONSE_NONE or r == gtk.RESPONSE_DELETE_EVENT:
                self.quit()
            uri = cm.get_connection_uri()
            name = cm.get_connection_name()
            cm.destroy()
            self.open_database(uri, name, True)
                
        # now that we have a connection build and show the gui
        self.gui = GUI(self)
        
        
    def delete_event(self, widget, event, data=None):
        print "delete_event"
        return gtk.FALSE


    def get_cursor(self):
        """return a connection to the database"""
        if self.conn == None: return None
        else: return self.conn.cursor()


    def create_database(self):
        msg = "Creating a new database on this connection could overwrite an "\
        "existing database. Are you sure you want to create a new database?"
        if not utils.yes_no_dialog(msg):
            return
        for t in tables.tables.values():
            try:
                t.dropTable()
            except Exception: pass
            t.createTable()
            
        
    #
    # tracing execution 
    #
    def mytrace(self, statement, binding):
        "Called just before executing each statement"
        print "SQL:",statement
        return True
    
    
    def build_connection_uri(self, params):
        template = "%(type)s://%(user)s:%(passwd)s@%(host)s/%(db)s"
        return template % params
                          
        
    def open_database(self, uri, name=None, before_main=False):        
        """
        open a database connection, will call get_passwd to popup a 
        dialog to enter the passwd
        TODO: would probably be less annoying if we tried to connect first
        without a passwd and only asked for a passwd if the first try failed
        """

        #sqlhub.threadConnection = connectionForURI(uri, debug=DEBUG_SQL, debugOutput=DEBUG_SQL)    
        sqlhub.threadConnection = connectionForURI(uri)    
        try:
            self.conn = sqlhub.threadConnection.getConnection() # i think this does the connecting
            self.conn.autoCommit = False
        except Exception, e:
            print e
            msg = "Could not open connection"
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        if name is not None:
            print "save preferences"
            Preferences[prefs.conn_default_pref] = name
            Preferences.save()
    
    def destroy(self, widget, data=None):
        gtk.main_quit()


    def save_state(self):
        # in case we quit before the gui is created
        if hasattr(self, "gui") and self.gui is not None:
            self.gui.save_state()
        Preferences.save()
        
        
    def quit(self):
        self.save_state()
        try:
            gtk.main_quit()
        except RuntimeError: # in case main_quit is called before main
            sys.exit(1)
            
    
    def main(self):
        # the docs say i should have these but they seem to lock up
        # everything
        #gtk.threads_enter()
        gtk.main()
        #gtk.threads_leave()


#
# main
#
if __name__ == "__main__":
    gtk.threads_init() # initialize threading
    Bauble().main()
