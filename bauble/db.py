#
# db.py
#

import os
import traceback
import gtk
import datetime
from sqlalchemy import *
import bauble
import bauble.pluginmgr as pluginmgr
import bauble.meta as meta
import bauble.utils as utils
from bauble.utils.log import debug
from bauble.i18n import *
from bauble.error import *
import logging

    # TODO: creating a database can't be guaranteed to work if you are
    # trying to create
    # a new database at a connection that has tables that aren't defined in
    # the current metadata, sqlalchemy won't be able to determine the
    # dependency order and you might get a drop...cascade error, we could
    # either pass drop all directly to the database, is this non-standard

    # TODO: what about leaving tables around that we're not using or indexes
    # or other things from other versions, is it possible to have a
    # "relatively" clean state, maybe if we hold a schema object in the
    # meta with at least the indexes and table names

    # TODO: should probably do a version check and make sure
    # that we aren't creating a new database on a database when the version
    # numbers don't match...in fact we shouldn't really allow creating a new
    # database except from the connection dialog so that we can't connect
    # to a database unless it was created by bauble

    # TODO: could keep a list of tables created by bauble in the database
    # which we could then reflect and drop, in general maybe we should have
    # more information about the schema represented in the datbase

def create(import_defaults=True):
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

    conn = default_metadata.engine.contextual_connect()
    transaction = conn.begin()
    try:
        # TODO: here we are creating all the tables in the metadata whether
        # they are in the registry or not, we should really only be creating
        # those tables in the registry
        default_metadata.drop_all()
        default_metadata.create_all()

        # TODO: clearing the insert menu probably shouldn't be here and should
        # probably be pushed into bauble.create_database, the problem is at the
        # moment the data is imported in the pluginmgr.init method so we would
        # have to separate table creations from the init menu

        # clear the insert menu
        if bauble.gui is not None and hasattr(bauble.gui, 'insert_menu'):
            menu = bauble.gui.insert_menu
            submenu = menu.get_submenu()
            for c in submenu.get_children():
                submenu.remove(c)
            menu.show()

        # TODO: this won't work correctly because importing the data
        # in the pluginmgr is non blocking and will return here and cause
        # the transaction to be committed before it's through
        # UPDATE: June 2, 2007 - is this still true, it looks like the
        # pluginmgr install blocks now

        # create the plugin registry and import the default data
        pluginmgr.install('all', import_defaults, force=True)
        #pluginmgr.init(True)
#        debug('returned from pluginmgr.install')
        meta.bauble_meta_table.insert().execute(name=meta.VERSION_KEY,
                                                value=str(bauble.version))
        meta.bauble_meta_table.insert().execute(name=meta.CREATED_KEY,
                                            value=str(datetime.datetime.now()))

    except Exception:
#        debug('rollback')
#        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
        transaction.rollback()
#        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
        raise
    else:
#        debug('commit')
#        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
        transaction.commit()
#        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    conn.close()

#    from bauble.plugins.plants.family import family_table
#    debug(select([family_table.c.family]).execute().fetchall())
#    debug('leaving db.create()')

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
        super(VersionError, self).__init__()
        self.version = version


def verify(engine):
    # make sure the version information matches or if the bauble
    # table doesn't exists then this may not be a bauble created
    # database
    warning = _('\n\n<i>Warning: If a database does already exists at ' \
                'this connection, creating a new database could corrupt '\
                'it.</i>')
    session = create_session()
    query = session.query(meta.BaubleMeta)


    # check that the database we connected to has the bauble meta table
    if not engine.has_table(meta.bauble_meta_table.name):
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
        raise VersionError(result.value)

    return True
#    # check that the database we connected has a "registry" in the bauble
#    # meta table
#    result = query.get_by(name=meta.REGISTRY_KEY)
#    if result is None:
#        raise RegistryError()



def open(uri):
    """
    open a database connection

    @param uri: the uri of the database to open
    """
    #debug(uri) # ** WARNING: this can print your passwd
    db_engine = None
    try:
        global_connect(uri)#, strategy='threadlocal')
        default_metadata.engine.contextual_connect() # test the connection
        db_engine = default_metadata.engine
    except Exception, e:
        msg = _("Could not open connection.\n\n%s") % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     gtk.MESSAGE_ERROR)
        return None

    return db_engine
