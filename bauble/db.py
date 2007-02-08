import os
import datetime
from sqlalchemy import *
import bauble
import bauble.pluginmgr as pluginmgr
import bauble.meta as meta
from bauble.i18n import *
from bauble.error import *

def create():
    """
    create new Bauble database at the current connection

    this will drop _all_ the tables at the connection that are registered with
    the metadata

    NOTE: since we can only drop tables that are registered with the database
    then its possible that some tables won\'t be dropped
    """
    # TODO: when creating a database there shouldn't be any errors
    # on import since we are importing from the default values, we should
    # just force the import and send everything in the database at once
    # instead of using slices, this would make it alot faster but it may 
    # make it more difficult to make the interface more responsive,
    # maybe we can use a dialog without the progress bar to show the status,
    # should probably work on the status bar to display this
    # TODO: *** important ***
    # this work should be done in a transaction, i think the best way to do
    # this would be to pass a metadata or engine or connection object to
    # the importer that holds the transaction we should work in    
    default_filenames = []
    default_metadata.drop_all()
    default_metadata.create_all()

    # create the plugin registry and import the default data
    pluginmgr.init(True) 
    meta.bauble_meta_table.insert().execute(name=meta.VERSION_KEY, 
                                            value=str(bauble.version))
    meta.bauble_meta_table.insert().execute(name=meta.CREATED_KEY,
                                            value=str(datetime.datetime.now()))

class DatabaseError(BaubleError):
    pass

class MetaTableError(DatabaseError):
    pass

class TimestampError(DatabaseError):
    pass

class RegistryError(DatabaseError):
    pass

class VersionError(DatabaseError):    
    def __init__(self, version):
        self.version = version


def open(uri):
    """
    open a database connection
    
    @param uri: the uri of the database to open
    """
    #debug(uri) # ** WARNING: this can print your passwd
    db_engine = None
    try:
        global_connect(uri)
        default_metadata.engine.connect() # test the connection
        db_engine = default_metadata.engine
    except Exception, e:
        msg = "Could not open connection.\n\n%s" % utils.xml_safe(e)
        utils.message_details_dialog(msg, traceback.format_exc(), 
                                     gtk.MESSAGE_ERROR)
        return None                                

    # make sure the version information matches or if the bauble
    # table doesn't exists then this may not be a bauble created 
    # database
    warning = _('\n\n<i>Warning: If a database does already exists at ' \
                'this connection, creating a new database could corrupt '\
                'it.</i>')
    session = create_session()
    query = session.query(meta.BaubleMeta)
    
    
    # check that the database we connected to has the bauble meta table
    if not db_engine.has_table(meta.bauble_meta_table.name):
        raise MetaTableError()

    # check that the database we connected to has a "created" timestamp
    # in the bauble meta table
    result = query.get_by(name=meta.CREATED_KEY)
    if result is None:            
        raise TimestampError()
    
    # check that the database we connected to has a "version" in the bauble
    # meta table and the the major and minor version are the same
    result = query.get_by(name=meta.VERSION_KEY)
    if result is None:
        raise VersionError(None)    
    elif eval(result.value)[0:2] != bauble.version[0:2]:
        raise VersionError(result)        
    
#    # check that the database we connected has a "registry" in the bauble
#    # meta table
#    result = query.get_by(name=meta.REGISTRY_KEY)
#    if result is None:
#        raise RegistryError()

    return db_engine
