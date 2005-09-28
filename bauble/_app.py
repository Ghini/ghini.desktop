#
# app.py
#
# NOTE: only bauble.py should import this modules


import os, sys
import gtk
from sqlobject import *
import bauble.utils as utils
from bauble.plugins import plugins
from bauble.prefs import prefs
from bauble.utils.log import debug

DEBUG_SQL = False

class BaubleApp:
    
    def __init__(self):
        self.gui = None
    

    def delete_event(self, widget, event, data=None):
        # when is this ever called? why is it here
        print "BaubleApp.delete_event"
        return gtk.FALSE


#    def get_cursor(self):
#        """return a connection to the database"""
#        if self.conn == None: return None
#        else: return self.conn.cursor()


    def create_database(self):
        #msg = "Creating a new database on this connection could overwrite an "\
        #"existing database. Are you sure you want to create a new database?"
        # 
        # TODO: we should drop the entire database or we can get ghost tables
        # that aren't being using by plugins anymore
        #
        msg = "If a database already exists at this connection then creating " \
              "a new database will delete the old database.\n\nAre you sure " \
              "this is what you want to do?"
        if not utils.yes_no_dialog(msg):
            return
        import pysqlite2.dbapi2
        try:
            for p in plugins.values():
                p.create_tables()
        except pysqlite2.dbapi2.OperationalError:
            msg = "Error creating the database. This sometimes happens " \
            "when trying to create a SQLite database on a network drive. " \
            "Try creating the database in a local drive or folder."
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)


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
            #uri += "?check_same_thread=0" # incase using multiple threads
#            uri += "&autoCommit=0"        
            pass
        #debug(uri) # this can print your passwd
        sqlhub.processConnection = connectionForURI(uri)
#        if debug.enabled:
#            # should do something like debug_sql=True and debug_sql_output=True
#            sqlhub.processConnection.debug = True
#            sqlhub.processConnection.debugOutput = True
        try:
            # make the connection, we don't really need the connection,
            # we just want to make sure we can connect
            #self.conn = sqlhub.getConnection().getConnection() 
            #self.conn = sqlhub.getConnection()
            #self.conn = sqlhub.processConnection
            sqlhub.processConnection.getConnection()
            # if not autocommit then mysql import won't work unless we 
            # temporary store autocommit and restore it to the original
            # values, either way why would we want autocommit false
            #self.conn.autoCommit = False 
        except Exception, e:
            msg = "Could not open connection.\n\n%s" % str(e)
            print msg
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            return False
                    
        if name is not None:
            prefs[prefs.conn_default_pref] = name
            prefs.save()
        return True
        
    def destroy(self, widget, data=None):
        gtk.main_quit()


    def save_state(self):
        # in case we quit before the gui is created
        if hasattr(self, "gui") and self.gui is not None:
            self.gui.save_state()
        prefs.save()
        
        
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
        
        #from bauble.plugins import plugins
        import bauble.plugins
        # intialize the plugins        
        #plugins()
        #plugins.load()
        #plugins.init()
        bauble.plugins.init_plugins()
        
        # open default database on startup
        # import these here to avoid recursive import hell
        import bauble._gui as gui
        from bauble.conn_mgr import ConnectionManagerDialog
        #self.conn = None
        default_conn = prefs[prefs.conn_default_pref]
        while True:
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
            if self.open_database(uri, name, True):
                break
                        
        
        # now that we have a connection build and show the gui
        self.gui = gui.GUI(self)
#        gtk.threads_enter()
        gtk.main()
#        gtk.threads_leave()


#baubleApp = BaubleApp()
#import bauble
