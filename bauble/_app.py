#
# app.py
#
# NOTE: only bauble.py should import this modules

import os, sys, traceback
import gtk
from sqlalchemy import *
from bauble.plugins import plugins, tools, views, editors
import bauble.utils as utils
from bauble.prefs import prefs
from bauble.utils.log import debug
import datetime
import bauble
import bauble.meta as meta

DEBUG_SQL = False

class BaubleApp(object):
    
    conn_name = None
    gui = None
    db_engine = None

    @staticmethod
    def create_database():
        '''
        create new Bauble database at the current connection
        '''
        # TODO: when creating a database there shouldn't be any errors
        # on import since we are importing from the default values, we should
        # just force the import and send everything in the database at once
        # instead of using slices, this would make it alot faster but it may 
        # make it more difficult to make the interface more responsive,
        # maybe we can use a dialog without the progress bar to show the status,
        # should probably work on the status bar to display this
        bauble.app.set_busy(True)
        # drop all tables
        
        default_filenames = []
        try:
            default_metadata.drop_all()
            default_metadata.create_all()
            
            for p in plugins.values():
                default_filenames.extend(p.default_filenames())
            
            default_basenames = [os.path.basename(f) for f in default_filenames]                        
            # import default data
            if len(default_filenames) > 0:
                from bauble.plugins.imex_csv import CSVImporter
                csv = CSVImporter()    
                csv.start(default_filenames)
            
            # add the version to the meta table
            meta.bauble_meta_table.insert().execute(name=meta.VERSION_KEY,
                                                    value=str(bauble.version))
        except:
            msg = "Error creating tables. Your database may be corrupt."
            utils.message_details_dialog(msg, traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)
            # TODO: should be do a rollback here so that we return to the previous
            # database state, we would first need a begiin at the beginning of 
            # this method for it to work correction i think
            # UPDATE: this wouldn't work since csv.start() doesn't block, need 
            # another way to handle the transaction, maybe pass it the csv start
            # and tell it to commit when it's done. that not good though.
        else:
            # create the created timestamp
            meta.bauble_meta_table.insert().execute(name=meta.CREATED_KEY,
                                          value=str(datetime.datetime.now()))
                           
        bauble.app.set_busy(False)
        
    
    def set_busy(self, busy):
        if self.gui is None:
            return
        self.gui.window.set_sensitive(not busy)
        if busy:
            self.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        else:
            self.gui.window.window.set_cursor(None)
            
            
    def build_connection_uri(self, params):
        template = "%(type)s://%(user)s:%(passwd)s@%(host)s/%(db)s"
        return template % params
                          
                          
    @classmethod
    def open_database(cls, uri, name=None):
        """
        open a database connection
        """
        #debug(uri) # ** WARNING: this can print your passwd
        try:
            global_connect(uri)
            cls.db_engine = default_metadata.engine
        except Exception, e:
            msg = "Could not open connection.\n\n%s" % str(e)        
            utils.message_details_dialog(msg, traceback.format_exc(), 
                                         gtk.MESSAGE_ERROR)
            cls.conn_name = None
            return None
                                    
        if name is not None:
            prefs[prefs.conn_default_pref] = name
            prefs.save()
    
        # make sure the version information matches or if the bauble
        # table doesn't exists then this may not be a bauble created 
        # database
        warning = "\n\n<i>Warning: If a database does already exists at this "\
                  "connection, creating a new database could corrupt it.</i>"
        session = create_session()
        query = session.query(meta.BaubleMetaTable)
        try:            
            result = query.get_by(name=meta.VERSION_KEY)
            if result is not None:            
                db_version = eval(result.value)            
            if result is not None and db_version[0:2] != bauble.version[0:2]:# compare major and minor
                msg = 'You are using Bauble version %d.%d.%d while the '\
                      'database you have connected to was created with '\
                      'version %d.%d.%d\n\nSome things might not work as '\
                      'or some of your data may become unexpectedly '\
                      'corrupted.'\
                      % (bauble.version[0], bauble.version[1], \
                         bauble.version[2], db_version[0], db_version[1], \
                         db_version[2],)
                utils.message_dialog(msg, gtk.MESSAGE_WARNING)       
                            
            result = query.get_by(name=meta.CREATED_KEY)
            if result is None:            
                msg = 'The database you have connected to does not have a '\
                      'timestamp for when it was created. This usually means '\
                      'that there was a problem when you created the '\
                      'database.  You like to try to create the database '\
                      'again?' + warning
                if utils.yes_no_dialog(msg):
                    cls.create_database()
                    cls.conn_name = name
                    return cls.open_database(uri, name)
                else:
                    cls.conn_name = None
                    return None
                        
        except Exception:
            debug(traceback.format_exc())
            msg = "The database you have connected to is either empty or " \
                  "wasn't created using Bauble. Would you like to create a " \
                  "create a database at this connection?" + warning
            if utils.yes_no_dialog(msg):
                cls.create_database()
                cls.conn_name = name
                return cls.open_database(uri, name)
            else:
                cls.conn_name = None
                return None
    	cls.conn_name = name
        return cls.db_engine        
        
        
    def destroy(self, widget, data=None):
        gtk.main_quit()


    def save_state(self):
        # in case we quit before the gui is created
        if hasattr(self, "gui") and self.gui is not None:
            self.gui.save_state()
        prefs.save()
        
        
    def quit(self):
        self.save_state()
        try:
            gtk.main_quit()
        except RuntimeError: # in case main_quit is called before main
            sys.exit(1)
            
    
    def main(self):
        prefs.init() # intialize the preferences
        bauble.plugins.init_plugins() # intialize the plugins      
        
        # open default database on startup        
        from bauble.conn_mgr import ConnectionManager
        default_conn = prefs[prefs.conn_default_pref]
        while True:            
            cm = ConnectionManager(default_conn)            
            conn_name, uri = cm.start()
            if conn_name is None:
                self.quit()
            if self.open_database(uri, conn_name):
                break
                                
        # now that we have a connection create the gui
        import bauble._gui as gui
        self.gui = gui.GUI()
        
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
        
        bauble.plugins.start_plugins()
        gtk.main()
