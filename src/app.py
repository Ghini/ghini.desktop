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
        #print "Bauble.open_database: " + uri
        #sqlhub.threadConnection = connectionForURI(uri, debug=DEBUG_SQL, debugOutput=DEBUG_SQL)    
        #sqlhub.threadConnection = connectionForURI(uri)    
        sqlhub.processConnection = connectionForURI(uri)    
        try:
            # make the connection
            #self.conn = sqlhub.threadConnection.getConnection() 
            self.conn = sqlhub.processConnection.getConnection() 
            if hasattr(self.conn, "autoCommit"): # sqlite doesn't have i guess
                self.conn.autoCommit = False
        except Exception, e:
            print e
            msg = "Could not open connection"
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
        
        if name is not None:
            #print "save preferences"
            #Preferences[prefs.conn_default_pref] = name
            #Preferences.save()
            #import bauble
            bauble.prefs[bauble.prefs.conn_default_pref] = name
    
    def destroy(self, widget, data=None):
        gtk.main_quit()


    def save_state(self):
        # in case we quit before the gui is created
        if hasattr(self, "gui") and self.gui is not None:
            self.gui.save_state()
        bauble.prefs.save()
        #Preferences.save()
        
        
    def quit(self):
        self.save_state()
        try:
            gtk.main_quit()
        except RuntimeError: # in case main_quit is called before main
            sys.exit(1)
            
    
    def main(self):
        # the docs say i should have these but they seem to lock up
        # everything
        # open default database on startup
        # import these here to avoid recursive import hell
        import gui
        from conn_mgr import ConnectionManagerDialog
        self.conn = None
        #default_conn = Preferences[prefs.conn_default_pref]
        default_conn = bauble.prefs[bauble.prefs.conn_default_pref]
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
        self.gui = gui.GUI(self)
        #gtk.threads_enter()
        gtk.main()
        #gtk.threads_leave()


baubleApp = BaubleApp()
import bauble
