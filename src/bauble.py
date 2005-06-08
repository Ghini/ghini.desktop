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

# is this the best way to add lib to the load path???
path, name = os.path.split(__file__)
sys.path.append(path + os.sep + "lib")


import pygtk
pygtk.require("2.0")
import gtk
from sqlobject import *

from gui import *
import tables
from prefs import Preferences


#
# Bauble
#                    
class Bauble:
    
    conn_default_pref = "conn.default"
    conn_list_pref = "conn.list"
    
    def __init__(self):
        # keep the directory where this resides for loading local files
        self.path, dummy = os.path.split(__file__)

        # open default database on startup
        self.conn = None
        num_tries = 0
        while self.conn is None:
            params = Preferences[self.conn_default_pref]
            if params is None or num_tries >= 2:
                cm = ConnectionManagerGUI()
                params = cm.get_connection_parameters(before_main=True)
            if params is None: self.quit()
            self.open_database(params, True)
            num_tries += 1
                
        # now that we have a connection build and show the gui
        self.gui = GUI(self)
        
        
    def delete_event(self, widget, event, data=None):
        print "delete_event"
        return gtk.FALSE


    def get_cursor(self):
        """return a connection to the database"""
        if self.conn == None: return None
        else: return self.conn.cursor()


    def create_database(self, params):
        # TODO: first we should connect with a uri that doesn't use the db
        # parameter and check if the database exists, if it doesn't we should
        # ask the user if they would like to create it or if so then should we
        # overwrite
        #
        # i'm not sure how cross platform CREATE DATABASE, DROP DATABASE,
        # and USE statements are so this may bork on some platforms

        self.open_database(params)
        #uri = self.build_connection_uri(params)
        #self.conn = dbmgr.connect(uri)
        # i don't know if this is allowed on all databases
        #self.conn.query("USE bbg_new2;")        
        # TODO: should check here if the database already exists
        # and aks the user if they would like to delete the database
        try:
            self.conn.query("CREATE DATABASE " + params["db"])
        except: # ProgrammingError, e:
            msg = "** Error -- Could not create database. " + \
                  "Check connection parameters are correct, that " + \
                  "you have the correct permissions and that the database " +\
                  "does not already exists. Would you still like to " + \
                  "create the database?"
            d = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION,
                                  gtk.BUTTONS_YES_NO, msg)
            r = d.run()
            d.destroy()
            if r == gtk.RESPONSE_NO:
                return
            
        try:
            self.conn.query("DROP DATABASE " + params["db"])
            self.conn.query("CREATE DATABASE " + params["db"])
            self.conn.query("USE " + params["db"])
            tables.create_tables()
        except Exception, e:
            msg = "** Error -- Could not create database."
            d = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                                  gtk.BUTTONS_YES_NO, msg)
            r = d.run()            
            d.destroy()
        return
            
        
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
               
       
    def get_passwd(self, before_main=False):
        d = gtk.Dialog("Enter your password", None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250,-1)
        entry = gtk.Entry()
        entry.set_visibility(False)
        entry.connect("activate", lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        if before_main:
            gtk.threads_enter()
        d.run()
        if before_main:
            gtk.threads_leave()
        passwd = entry.get_text()
        d.destroy()
        return passwd
            
        
    def open_database(self, params, before_main=False):        
        """
        open a database connection, will call get_passwd to popup a 
        dialog to enter the passwd
        TODO: would probably be less annoying if we tried to connect first
        without a passwd and only asked for a passwd if the first try failed
        """
        passwd = None
        if not params.has_key("passwd"):
            while passwd == None:
                passwd = self.get_passwd(before_main)            
     
        params["passwd"] = passwd
        params["type"] = params["type"].lower() # lowercase the database type
        uri = self.build_connection_uri(params)
        sqlhub.threadConnection = connectionForURI(uri)
        try:
            del params["passwd"] # so it doesn't get stored in prefs
            self.conn = sqlhub.threadConnection.getConnection() # i think this does the connecting
            self.conn.autoCommit = False
            Preferences[self.conn_default_pref] = params
        except Exception, e:
            d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  type=gtk.MESSAGE_ERROR,
                                  buttons = gtk.BUTTONS_OK, 
                                  message_format="Could not open connection")
            if before_main:
                gtk.threads_enter()
            d.run()
            if before_main:
                gtk.threads_leave()
            d.destroy()
        
    
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
        gtk.threads_enter()
        gtk.main()
        gtk.threads_leave()


#
# main
#
if __name__ == "__main__":
    gtk.threads_init() # initialize threading
    Bauble().main()
