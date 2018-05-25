# -*- coding: utf-8 -*-
#
# Copyright 2005-2010 Brett Adams <brett@belizebotanic.org>
# Copyright 2015-2017 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
# Copyright 2018 Ilja Everilä
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.

import gi
gi.require_version('Gtk', '3.0')

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from sqlalchemy.orm import class_mapper

import datetime
import os
import re
import bauble.error as error
import json
from bauble.utils import parse_date


try:
    import sqlalchemy as sa
    parts = tuple(int(i) for i in sa.__version__.split('.')[:2])
    if parts < (0, 6):
        msg = _('This version of Ghini requires SQLAlchemy 0.6 or greater. '
                'You are using version %s. '
                'Please download and install a newer version of SQLAlchemy '
                'from http://www.sqlalchemy.org or contact your system '
                'administrator.') % '.'.join(parts)
        raise error.SQLAlchemyVersionError(msg)
except ImportError:
    msg = _('SQLAlchemy not installed. Please install SQLAlchemy from '
            'http://www.sqlalchemy.org')
    raise


from gi.repository import Gtk

import sqlalchemy.orm as orm
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta

import bauble.btypes as types
import bauble.utils as utils


def sqlalchemy_debug(verbose):
    if verbose:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.orm.unitofwork').setLevel(logging.DEBUG)
    else:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)
        logging.getLogger('sqlalchemy.orm.unitofwork').setLevel(logging.WARN)

SQLALCHEMY_DEBUG = False
sqlalchemy_debug(SQLALCHEMY_DEBUG)


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.flush()
        return instance


def natsort(attr, obj):
    """return the naturally sorted list of the object attribute

    meant to be curried.  the main role of this function is to invert
    the order in which the function getattr receives its arguments.

    attr is in the form <attribute> but can also specify a path from the
    object to the attribute, like <a1>.<a2>.<a3>, in which case each
    step should return a single database object until the last step
    where the result should be a list of objects.

    e.g.:
    from functools import partial
    partial(natsort, 'accessions')(species)
    partial(natsort, 'species.accessions')(vern_name)
    """
    from bauble import utils
    jumps = attr.split('.')
    for attr in jumps:
        obj = getattr(obj, attr)
    return sorted(obj, key=utils.natsort_key)


class HistoryExtension(orm.MapperExtension):
    """
    HistoryExtension is a
    :class:`~sqlalchemy.orm.interfaces.MapperExtension` that is added
    to all clases that inherit from bauble.db.Base so that all
    inserts, updates, and deletes made to the mapped objects are
    recorded in the `history` table.
    """
    def _add(self, operation, mapper, connection, instance):
        """
        Add a new entry to the history table.
        """
        user = None
        try:
            if engine.name.startswith('sqlite'):
                raise TypeError("this engine know nothing of users")
            import bauble.plugins.users as users
            user = users.current_user()
        except:
            if 'USER' in os.environ and os.environ['USER']:
                user = os.environ['USER']
            elif 'USERNAME' in os.environ and os.environ['USERNAME']:
                user = os.environ['USERNAME']

        row = {}
        for c in mapper.local_table.c:
            row[c.name] = utils.utf8(getattr(instance, c.name))
        table = History.__table__
        stmt = table.insert(dict(table_name=mapper.local_table.name,
                                 table_id=instance.id, values=str(row),
                                 operation=operation, user=user,
                                 timestamp=datetime.datetime.today()))
        connection.execute(stmt)

    def after_update(self, mapper, connection, instance):
        self._add('update', mapper, connection, instance)

    def after_insert(self, mapper, connection, instance):
        self._add('insert', mapper, connection, instance)

    def after_delete(self, mapper, connection, instance):
        self._add('delete', mapper, connection, instance)


class MapperBase(DeclarativeMeta):
    """
    MapperBase adds the id, _created and _last_updated columns to all
    tables.

    In general there is no reason to use this class directly other
    than to extend it to add more default columns to all the bauble
    tables.
    """
    def __init__(cls, classname, bases, dict_):
        if '__tablename__' in dict_:
            cls.id = sa.Column('id', sa.Integer, primary_key=True,
                               autoincrement=True)
            cls._created = sa.Column('_created', types.DateTime(timezone=True),
                                     default=sa.func.now())
            cls._last_updated = sa.Column('_last_updated',
                                          types.DateTime(timezone=True),
                                          default=sa.func.now(),
                                          onupdate=sa.func.now())
            cls.__mapper_args__ = {'extension': HistoryExtension()}
        if 'top_level_count' not in dict_:
            cls.top_level_count = lambda x: {classname: 1}
        if 'search_view_markup_pair' not in dict_:
            cls.search_view_markup_pair = lambda x: (
                utils.xml_safe(str(x)),
                '(%s)' % type(x).__name__)

        super().__init__(classname, bases, dict_)


engine = None
"""A :class:`sqlalchemy.engine.base.Engine` used as the default
connection to the database.
"""


Session = None
"""
bauble.db.Session is created after the database has been opened with
:func:`bauble.db.open()`. bauble.db.Session should be used when you need
to do ORM based activities on a bauble database.  To create a new
Session use::Uncategorized

    session = bauble.db.Session()

When you are finished with the session be sure to close the session
with :func:`session.close()`. Failure to close sessions can lead to
database deadlocks, particularly when using PostgreSQL based
databases.
"""

Base = declarative_base(metaclass=MapperBase)
"""
All tables/mappers in Ghini which use the SQLAlchemy declarative
plugin for declaring tables and mappers should derive from this class.

An instance of :class:`sqlalchemy.ext.declarative.Base`
"""


metadata = Base.metadata
"""The default metadata for all Ghini tables.

An instance of :class:`sqlalchemy.schema.Metadata`
"""

history_base = declarative_base(metadata=metadata)


class History(history_base):
    """
    The history table records ever changed made to every table that
    inherits from :ref:`Base`

    :Table name: history

    :Columns:
      id: :class:`sqlalchemy.types.Integer`
        A unique identifier.
      table_name: :class:`sqlalchemy.types.String`
        The name of the table the change was made on.
      table_id: :class:`sqlalchemy.types.Integer`
        The id in the table of the row that was changed.
      values: :class:`sqlalchemy.types.String`
        The changed values.
      operation: :class:`sqlalchemy.types.String`
        The type of change.  This is usually one of insert, update or delete.
      user: :class:`sqlalchemy.types.String`
        The name of the user who made the change.
      timestamp: :class:`sqlalchemy.types.DateTime`
        When the change was made.
    """
    __tablename__ = 'history'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    table_name = sa.Column(sa.Text, nullable=False)
    table_id = sa.Column(sa.Integer, nullable=False, autoincrement=False)
    values = sa.Column(sa.Text, nullable=False)
    operation = sa.Column(sa.Text, nullable=False)
    user = sa.Column(sa.Text)
    timestamp = sa.Column(types.DateTime, nullable=False)


def open(uri, verify=True, show_error_dialogs=False):
    """
    Open a database connection.  This function sets bauble.db.engine to
    the opened engined.

    Return bauble.db.engine if successful else returns None and
    bauble.db.engine remains unchanged.

    :param uri: The URI of the database to open.
    :type uri: str

    :param verify: Where the database we connect to should be verified
        as one created by Ghini.  This flag is used mostly for
        testing.
    :type verify: bool

    :param show_error_dialogs: A flag to indicate whether the error
        dialogs should be displayed.  This is used mostly for testing.
    :type show_error_dialogs: bool
    """

    # ** WARNING: this can print your passwd
    logger.debug('db.open(%s)' % uri)
    from sqlalchemy.orm import sessionmaker, scoped_session
    global engine
    new_engine = None

    from sqlalchemy.pool import SingletonThreadPool
    from bauble.prefs import testing

    poolclass = SingletonThreadPool
    new_engine = sa.create_engine(uri, echo=SQLALCHEMY_DEBUG,
                                  implicit_returning=False,
                                  poolclass=poolclass, pool_size=20)
    # TODO: there is a problem here: the code may cause an exception, but we
    # immediately loose the 'new_engine', which should know about the
    # encoding used in the exception string.
    try:
        new_engine.connect().close()  # make sure we can connect
    except Exception:
        logger.info('about to forget about encoding of exception text.')
        raise

    def _bind():
        """bind metadata to engine and create sessionmaker """
        global Session, engine
        engine = new_engine
        metadata.bind = engine  # make engine implicit for metadata
        def temp():
            import inspect
            logger.debug('creating session %s' % str(inspect.stack()[1]))
            return scoped_session(sessionmaker(bind=engine, autoflush=False))()
        Session = scoped_session(sessionmaker(bind=engine, autoflush=False))
        Session = temp

    if new_engine is not None and not verify:
        _bind()
        return engine
    elif new_engine is None:
        return None

    verify_connection(new_engine, show_error_dialogs)
    _bind()
    return engine


def create(import_defaults=True):
    """
    Create new Ghini database at the current connection

    :param import_defaults: A flag that is passed to each plugins
        install() method to indicate where it should import its
        default data.  This is mainly used for testing.  The default
        value is True
    :type import_defaults: bool

    """

    logger.debug('entered db.create()')
    if not engine:
        raise ValueError('engine is None, not connected to a database')
    import bauble
    import bauble.meta as meta
    from bauble import pluginmgr
    import datetime

    connection = engine.connect()
    transaction = connection.begin()
    try:
        # TODO: here we are dropping/creating all the tables in the
        # metadata whether they are in the registry or not, we should
        # really only be creating those tables from registered
        # plugins, maybe with an uninstall() method on Plugin
        metadata.drop_all(bind=connection, checkfirst=True)
        metadata.create_all(bind=connection)

        # fill in the bauble meta table and install all the plugins
        meta_table = meta.BaubleMeta.__table__
        meta_table.insert(bind=connection).\
            execute(name=meta.VERSION_KEY,
                    value=str(bauble.version)).close()
        import time
        tzlocal = datetime.timezone(-datetime.timedelta(hours=time.timezone/60/60))
        meta_table.insert(bind=connection).\
            execute(name=meta.CREATED_KEY,
                    value=str(datetime.datetime.now(tz=tzlocal))).close()
    except GeneratorExit as e:
        # this is here in case the main windows is closed in the middle
        # of a task
        # UPDATE 2009.06.18: i'm not sure if this is still relevant since we
        # switched the task system to use fibra...but it doesn't hurt
        # having it here until we can make sure
        logger.warning('bauble.db.create(): %s' % utils.utf8(e))
        transaction.rollback()
        raise
    except Exception as e:
        logger.warning('bauble.db.create(): %s' % utils.utf8(e))
        transaction.rollback()
        raise
    else:
        transaction.commit()
    finally:
        connection.close()

    connection = engine.connect()
    transaction = connection.begin()
    try:
        pluginmgr.install('all', import_defaults, force=True)
    except GeneratorExit as e:
        # this is here in case the main windows is closed in the middle
        # of a task
        # UPDATE 2009.06.18: i'm not sure if this is still relevant since we
        # switched the task system to use fibra...but it doesn't hurt
        # having it here until we can make sure
        logger.warning('bauble.db.create(): %s' % utils.utf8(e))
        transaction.rollback()
        raise
    except Exception as e:
        logger.warning('bauble.db.create(): %s' % utils.utf8(e))
        transaction.rollback()
        raise
    else:
        transaction.commit()
    finally:
        connection.close()


def verify_connection(engine, show_error_dialogs=False):
    """
    Test whether a connection to an engine is a valid Ghini database. This
    method will raise an error for the first problem it finds with the
    database.

    :param engine: the engine to test
    :type engine: :class:`sqlalchemy.engine.Engine`
    :param show_error_dialogs: flag for whether or not to show message
        dialogs detailing the error, default=False
    :type show_error_dialogs: bool
    """
    logger.debug('entered verify_connection(%s)' % show_error_dialogs)
    import bauble
    if show_error_dialogs:
        try:
            return verify_connection(engine, False)
        except error.EmptyDatabaseError:
            msg = _('The database you have connected to is empty.')
            utils.message_dialog(msg, Gtk.MessageType.ERROR)
            raise
        except error.MetaTableError:
            msg = _('The database you have connected to does not have the '
                    'bauble meta table.  This usually means that the database '
                    'is either corrupt or it was created with an old version '
                    'of Ghini')
            utils.message_dialog(msg, Gtk.MessageType.ERROR)
            raise
        except error.TimestampError:
            msg = _('The database you have connected to does not have a '
                    'timestamp for when it was created. This usually means '
                    'that there was a problem when you created the '
                    'database or the database you connected to wasn\'t '
                    'created with Ghini.')
            utils.message_dialog(msg, Gtk.MessageType.ERROR)
            raise
        except error.VersionError as e:
            msg = (_('You are using Ghini version %(version)s while the '
                     'database you have connected to was created with '
                     'version %(db_version)s\n\nSome things might not work as '
                     'or some of your data may become unexpectedly '
                     'corrupted.') %
                   {'version': bauble.version,
                    'db_version': '%s' % e.version})
            utils.message_dialog(msg, Gtk.MessageType.ERROR)
            raise

    # check if the database has any tables
    if len(engine.table_names()) == 0:
        raise error.EmptyDatabaseError()

    import bauble.meta as meta
    # check that the database we connected to has the bauble meta table
    if not engine.has_table(meta.BaubleMeta.__tablename__):
        raise error.MetaTableError()

    from sqlalchemy.orm import sessionmaker
    # if we don't close this session before raising an exception then we
    # will probably get deadlocks....i'm not really sure why
    session = sessionmaker(bind=engine)()
    query = session.query  # (meta.BaubleMeta)

    # check that the database we connected to has a "created" timestamp
    # in the bauble meta table.  we're not using the value though.
    result = query(meta.BaubleMeta).filter_by(name=meta.CREATED_KEY).first()
    if not result:
        session.close()
        raise error.TimestampError()

    # check that the database we connected to has a "version" in the bauble
    # meta table and the the major and minor version are the same
    result = query(meta.BaubleMeta).filter_by(name=meta.VERSION_KEY).first()
    if not result:
        session.close()
        raise error.VersionError(None)
    try:
        major, minor, revision = result.value.split('.')
    except Exception:
        session.close()
        raise error.VersionError(result.value)

    if major != bauble.version_tuple[0] or minor != bauble.version_tuple[1]:
        session.close()
        raise error.VersionError(result.value)

    session.close()
    return True


def make_note_class(name, compute_serializable_fields, as_dict=None, retrieve=None):
    class_name = str(name + 'Note')
    table_name = name.lower() + '_note'

    def is_defined(self):
        return bool(self.user and self.category and self.note)

    def is_empty(self):
        return not self.user and not self.category and not self.note

    def retrieve_or_create(cls, session, keys,
                           create=True, update=True):
        """return database object corresponding to keys
        """
        category = keys.get('category', '')
        
        # normally, it's one note per category, but for list values, and for
        # pictures, we can have more than one.
        if (create and (category.startswith('[') and category.endswith(']') or
                        category == '<picture>')):
            # dirty trick: making sure it's not going to be found!
            import uuid
            keys['category'] = str(uuid.uuid4())
        result = super(globals()[class_name], cls).retrieve_or_create(session, keys, create, update)
        keys['category'] = category
        if result:
            result.category = category
        return result

    def retrieve_default(cls, session, keys):
        q = session.query(cls)
        if name.lower() in keys:
            q = q.join(globals()[name]).filter(
                globals()[name].code == keys[name.lower()])
        if 'date' in keys:
            q = q.filter(cls.date == keys['date'])
        if 'category' in keys:
            q = q.filter(cls.category == keys['category'])
        try:
            return q.one()
        except:
            return None
    
    def as_dict_default(self):
        result = db.Serializable.as_dict(self)
        result[name.lower()] = getattr(self, name.lower()).code
        return result

    as_dict = as_dict or as_dict_default
    retrieve = retrieve or retrieve_default

    result = type(class_name, (Base, Serializable),
                  {'__tablename__': table_name,
                   '__mapper_args__': {'order_by': table_name + '.date'},

                   'date': sa.Column(types.Date, default=sa.func.now()),
                   'user': sa.Column(sa.Unicode(64)),
                   'category': sa.Column(sa.Unicode(32)),
                   'note': sa.Column(sa.UnicodeText, nullable=False),
                   name.lower() + '_id': sa.Column(sa.Integer, sa.ForeignKey(name.lower() + '.id'), nullable=False),
                   name.lower(): sa.orm.relation(name, uselist=False, backref=sa.orm.backref(
                       'notes', cascade='all, delete-orphan')),
                   'retrieve': classmethod(retrieve),
                   'retrieve_or_create': classmethod(retrieve_or_create),
                   'compute_serializable_fields': classmethod(compute_serializable_fields),
                   'is_defined': is_defined,
                   'as_dict': as_dict,
                  })
    return result


class WithNotes:

    key_pattern = re.compile(r'{[^:]+:(.*)}')

    def __getattr__(self, name):
        '''retrieve value from corresponding note(s)

        the result can be an atomic value, a list, or a dictionary.
        '''

        if name.startswith('_sa'):  # it's a SA field, don't even try to look it up
            raise AttributeError(name)
        
        result = []
        is_dict = False
        for n in self.notes:
            if n.category == ('[%s]' % name):
                result.append(n.note)
            elif n.category.startswith('{%s:' % name) and n.category.endswith('}'):
                is_dict = True
                match = self.key_pattern.match(n.category)
                key = match.group(1)
                result.append((key, n.note))
            elif n.category == ('<%s>' % name):
                try:
                    return json.loads(re.sub(r'(\w+)[ ]*(?=:)', r'"\g<1>"', '{' + n.note.replace(';', ',') + '}'))
                except Exception as e:
                    pass
                try:
                    return json.loads(re.sub(r'(\w+)[ ]*(?=:)', r'"\g<1>"', n.note))
                except Exception as e:
                    logger.debug('not parsed %s(%s), returning literal text »%s«', type(e), e, n.note)
                    return n.note
        if result == []:
            # if nothing was found, do not break the proxy.
            raise AttributeError(name)
        if is_dict:
            return dict(result)
        return result


class DefiningPictures:

    @property
    def pictures(self):
        '''a list of Gtk.Image objects
        '''

        result = []
        for n in self.notes:
            if n.category != '<picture>':
                continue
            box = Gtk.VBox()  # contains the image or the error message
            utils.ImageLoader(box, n.note).start()
            result.append(box)
        return result


class Serializable:
    import re
    single_cap_re = re.compile('([A-Z])')
    link_keys = []

    def as_dict(self):
        result = dict((col, getattr(self, col))
                      for col in list(self.__table__.columns.keys())
                      if col not in ['id']
                      and col[0] != '_'
                      and getattr(self, col) is not None
                      and not col.endswith('_id'))
        result['object'] = self.single_cap_re.sub(
            r'_\1', self.__class__.__name__).lower()[1:]
        return result

    @classmethod
    def correct_field_names(cls, keys):
        """correct keys dictionary according to class attributes

        exchange format may use different keys than class attributes
        """
        pass

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        """create objects corresponding to keys (class dependent)
        """
        return {}

    @classmethod
    def retrieve_or_create(cls, session, keys,
                           create=True, update=True):
        """return database object corresponding to keys
        """

        logger.debug('initial value of keys: %s' % keys)
        ## first try retrieving
        is_in_session = cls.retrieve(session, keys)
        logger.debug('2 value of keys: %s' % keys)

        if not create and not is_in_session:
            logger.debug('not creating from %s; returning None (1)' % str(keys))
            return None

        if is_in_session and not update:
            logger.debug("returning not updated existing %s" % is_in_session)
            return is_in_session

        try:
            ## some fields are given as text but actually correspond to
            ## different fields and should be associated to objects
            extradict = cls.compute_serializable_fields(
                session, keys)

            ## what fields must be corrected
            cls.correct_field_names(keys)
        except error.NoResultException:
            if not is_in_session:
                logger.debug("returning None (2)")
                return None
            else:
                extradict = {}
        except Exception as e:
            logger.debug("this was unexpected")
            raise
            
        logger.debug('3 value of keys: %s' % keys)

        # correct any timestamp, parsing it as good as possible
        for k in ['_created', '_last_updated']:
            if k in keys:
                keys[k] = parse_date(keys[k])
        
        logger.debug('3½ value of keys: %s' % keys)

        ## at this point, resulting object is either in database or not. in
        ## either case, the database is going to be updated.

        ## link_keys are python-side properties, not database associations
        ## and have as value objects that are possibly in the database, or
        ## not, but they cannot be used to construct the `self` object.
        link_values = {}
        for k in cls.link_keys:
            if keys.get(k):
                link_values[k] = keys[k]

        logger.debug("link_values : %s" % str(link_values))

        for k in list(keys.keys()):
            if k not in class_mapper(cls).mapped_table.c:
                del keys[k]
        if 'id' in keys:
            del keys['id']
        logger.debug('4 value of keys: %s' % keys)

        keys.update(extradict)
        logger.debug('5 value of keys: %s' % keys)

        # early construct object before building links
        if not is_in_session and create:
            ## completing the task of building the links
            logger.debug("links? %s, %s" % (cls.link_keys, list(keys.keys())))
            for key in cls.link_keys:
                d = link_values.get(key)
                if d is None:
                    continue
                logger.debug('recursive call to construct_from_dict %s' % d)
                obj = construct_from_dict(session, d)
                keys[key] = obj
            logger.debug("going to create new %s with %s" % (cls, keys))
            result = cls(**keys)
            session.add(result)

        # or possibly reuse existing object
        if is_in_session and update:
            result = is_in_session

            ## completing the task of building the links
            logger.debug("links? %s, %s" % (cls.link_keys, list(keys.keys())))
            for key in cls.link_keys:
                d = link_values.get(key)
                if d is None:
                    continue
                logger.debug('recursive call to construct_from_dict %s' % d)
                obj = construct_from_dict(session, d)
                keys[key] = obj

        logger.debug("going to update %s with %s" % (result, keys))
        if 'id' in keys:
            del keys['id']
        for k, v in list(keys.items()):
            if isinstance(v, dict):
                if v.get('__class__') == 'datetime':
                    m = v.get('millis', 0)
                    v = datetime.datetime(1970, 1, 12)
                    v = v + datetime.timedelta(0, m)
                else:
                    v = None
            if v is not None:
                setattr(result, k, v)
        logger.debug('returning updated existing %s' % result)

        session.flush()

        logger.debug('returning new %s' % result)
        return result


def construct_from_dict(session, obj, create=True, update=True):
    ## get class and remove reference
    logger.debug("construct_from_dict %s" % obj)
    klass = None
    if 'object' in obj:
        klass = class_of_object(obj['object'])
    if klass is None and 'rank' in obj:
        klass = globals().get(obj['rank'].capitalize())
        del obj['rank']
    return klass.retrieve_or_create(session, obj, create=create, update=update)


def class_of_object(o):
    """what class implements object o
    """

    name = ''.join(p.capitalize() for p in o.split('_'))
    cls = globals().get(name)
    if cls is None:
        from bauble import pluginmgr
        cls = pluginmgr.provided.get(name)
    return cls
