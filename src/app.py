#
# app.py
#
# NOTE: only bauble.py should import this modules


import os, sys
import utils
import gtk
from sqlobject import *
#from conn_mgr import *

import tables
#import prefs
#from prefs import Preferences


DEBUG_SQL = False

class BaubleApp:
    
    def __init__(self):
        pass
    

    def delete_event(self, widget, event, data=None):
        # when is this ever called? why is it here
        print "BaubleApp.delete_event"
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
            
        # TODO: need to import those tables that are required for basic
        # functionality, Areas, Regions, States, Places, Families, 
        # Genera?
        
        # TODO: show a progress dialog about what stage in the database 
        # creation process we're in
        
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
        open a database connection
        """
        import sqlobject.sqlite.sqliteconnection as sqlite
        if uri.startswith('sqlite:'):# and sqlite.using_sqlite2:
            uri += "?check_same_thread=0"
#            uri += "&autoCommit=0"
        print uri
        sqlhub.processConnection = connectionForURI(uri)    
        try:
            # make the connection, we don't really need the connection,
            # we just want to make sure we can connect
            self.conn = sqlhub.getConnection() 
            # if not autocommit then mysql import won't work unless we 
            # temporary store autocommit and restore it to the original
            # values, either way why would we want autocommit false
            #self.conn.autoCommit = False 
        except Exception, e:
            print e
            msg = "Could not open connection"
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        if name is not None:
            bauble.prefs[bauble.prefs.conn_default_pref] = name
            bauble.prefs.save()
            
        
    def destroy(self, widget, data=None):
        gtk.main_quit()


    def save_state(self):
        # in case we quit before the gui is created
        if hasattr(self, "gui") and self.gui is not None:
            self.gui.save_state()
        bauble.prefs.save()
        
        
    def quit(self):
        # TODO: need to sync tables
        #for t in tables.tables.values():
        #    t.sync()
        self.save_state()
        try:
            gtk.main_quit()
        except RuntimeError: # in case main_quit is called before main
            sys.exit(1)
            
    
    def main(self):
        # open default database on startup
        # import these here to avoid recursive import hell
        import gui
        from conn_mgr import ConnectionManagerDialog
        self.conn = None
        default_conn = bauble.prefs[bauble.prefs.conn_default_pref]
        while self.conn is None:
            #gtk.gdk.threads_enter()
            cm = ConnectionManagerDialog(default_conn)
            r = cm.run()
            if r == gtk.RESPONSE_CANCEL or r == gtk.RESPONSE_CLOSE or \
               r == gtk.RESPONSE_NONE or r == gtk.RESPONSE_DELETE_EVENT:
                self.quit()
            uri = cm.get_connection_uri()
            name = cm.get_connection_name()
            cm.destroy()
            #gtk.gdk.threads_leave()
            self.open_database(uri, name, True)
                
        # now that we have a connection build and show the gui
        self.gui = gui.GUI(self)
#        gtk.threads_enter()
        gtk.main()
#        gtk.threads_leave()


baubleApp = BaubleApp()
import bauble
