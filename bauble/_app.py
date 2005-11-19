#
# app.py
#
# NOTE: only bauble.py should import this modules

import os, sys, traceback
import gtk
from sqlobject import *
from bauble.plugins import plugins, tools, views, editors
import bauble.utils as utils
from bauble.plugins import plugins
from bauble.prefs import prefs
from bauble.utils.log import debug
import datetime
import bauble

DEBUG_SQL = False

class BaubleApp:
    
    def __init__(self):
        self.gui = None
    

    def delete_event(self, widget, event, data=None):
        # when is this ever called? why is it here
        print "BaubleApp.delete_event"
        return gtk.FALSE


    def create_database(self):
        '''
        create new Bauble database at the current connection
        '''
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
            
        # TODO: this bails is pysqlite2 isn't installed
#        has_pysqlite2 = True
#        try:        
#            import pysqlite2.dbapi2
#        except ImportError:
#            has_pysqlite2 = False
        
#        try:

        bauble.BaubleMetaTable.dropTable(ifExists=True)
        bauble.BaubleMetaTable.createTable(ifNotExists=True)  
        bauble.BaubleMetaTable(name=bauble.BaubleMetaTable.version,
                        value=str(bauble.version))
        bauble.BaubleMetaTable(name=bauble.BaubleMetaTable.created, 
                        value=str(datetime.datetime.now()))        
        
        for p in plugins.values():
            p.create_tables()
#        except pysqlite2.dbapi2.OperationalError:
#            msg = "Error creating the database. This sometimes happens " \
#            "when trying to create a SQLite database on a network drive. " \
#            "Try creating the database in a local drive or folder."
#            utils.message_dialog(msg, gtk.MESSAGE_ERROR)


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
#            should do something like debug_sql=True and debug_sql_output=True
#        sqlhub.processConnection.debug = True
#        sqlhub.processConnection.debugOutput = True
#        sqlhub.processConnection.autoCommit = False
        try:
            # make the connection, we don't really need the connection,
            # we just want to make sure we can connect
            sqlhub.processConnection.getConnection()
            # if not autocommit then mysql import won't work unless we 
            # temporary store autocommit and restore it to the original
            # values, either way why would we want autocommit false
            #self.conn.autoCommit = False 
        except Exception, e:
            msg = "Could not open connection.\n\n%s" % str(e)        
            utils.message_details_dialog(msg, traceback.format_exc(), 
                                         gtk.MESSAGE_ERROR)
            return False
                    
                    
        # make sure the version information matches or if the bauble
        # table doesn't exists then this may not be a bauble created 
        # database
        try:
            sel = bauble.BaubleMetaTable.selectBy(name=bauble.BaubleMetaTable.version)
            db_version = eval(sel[0].value)
            if db_version[0:2] != bauble.version[0:2]: # compare major and minor
                msg = 'You are using Bauble version %d.%d.%d while the '\
                      'database you have connected to was created with '\
                      'version %d.%d.%d\n\nSome things might not work as '\
                      'or some of your data may become unexpectedly corrupted.' \
                      % (bauble.version[0], bauble.version[1], \
                         bauble.version[2], db_version[0], db_version[1], \
                         db_version[2],)
                utils.message_dialog(msg, gtk.MESSAGE_WARNING)                    
        except Exception:
            #msg = 'The database you are trying to connect to does not seem ' \
            #      'to have been created by Bauble. Please check your ' \
            #      'connection parameters.'
            msg = "The database you have connected to is either empty or " \
                  "wasn't created using Bauble. Would you like to create a " \
                  "create a database at this connection?\n\n<i>Warning: If " \
                  "a database does already exists at this connection, " \
                  "creating a new database could corrupt it.</i>"            
            #utils.message_dialog(msg, gtk.MESSAGE_ERROR)            
            if utils.yes_no_dialog(msg):
                self.create_database()
                return self.open_database(uri, name, before_main)
            else:
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
        
        import bauble.plugins
        # intialize the plugins        
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
                        
        
        # now that we have a connection create the gui
        self.gui = gui.GUI(self)
        
        # load the last view open from the prefs
        v = prefs[self.gui.current_view_pref]
        if v is None: # default view is the search view            
            v = str(views["SearchView"])
    
        view_set = False
        for name, view in views.iteritems():
            if v == str(view):
                self.gui.set_current_view(view)
                view_set = True
                # TODO: if this view can't be shown then default to SearchView
                
        if not view_set:
            self.gui.set_current_view(views["SearchView"])
        
        
#        gtk.threads_enter()
        gtk.main()
#        gtk.threads_leave()
