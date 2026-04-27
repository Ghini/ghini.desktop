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
import datetime
import json
import logging
import os
import re
from gettext import gettext as __
from typing import Any, Iterable, Optional

import bauble.btypes as types
import bauble.error as error
import bauble.utils as utils
import sqlalchemy.orm as orm
from bauble.gtkinit import Gtk
from bauble.utils import parse_date
from sqlalchemy import asc, event, insert, inspect, select, text
from sqlalchemy.engine import Connection

# from sqlalchemy import text
from sqlalchemy.orm import (
    DeclarativeMeta,
    Mapped,
    class_mapper,
    declarative_base,
    mapped_column,
)
from sqlalchemy.sql.sqltypes import String, Text, Unicode, UnicodeText

logger: Any = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


try:
    import sqlalchemy as sa

    parts: Any = tuple(int(i) for i in sa.__version__.split(".")[:2])
    if parts < (0, 6):
        msg = __(
            "This version of Ghini requires SQLAlchemy 0.6 or greater. "
            "You are using version %s. "
            "Please download and install a newer version of SQLAlchemy "
            "from http://www.sqlalchemy.org or contact your system "
            "administrator."
        ) % ".".join(parts)
        raise error.SQLAlchemyVersionError(msg)
except ImportError:
    msg: Any = __(
        "SQLAlchemy not installed. Please install SQLAlchemy from "
        "http://www.sqlalchemy.org"
    )
    raise


def sqlalchemy_debug(verbose) -> None:
    if verbose:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        logging.getLogger("sqlalchemy.orm.unitofwork").setLevel(logging.DEBUG)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARN)
        logging.getLogger("sqlalchemy.orm.unitofwork").setLevel(logging.WARN)


SQLALCHEMY_DEBUG: bool = False
sqlalchemy_debug(SQLALCHEMY_DEBUG)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


def get_or_create(session, model, defaults: Optional[Any] = None, **kwargs):
    """
    Retrieve or create an instance of the given model.

    :param session: SQLAlchemy session.
    :param model: The model class.
    :param defaults: Optional dictionary of default values to use if creating a new instance.
    :param kwargs: Filtering criteria for retrieving the instance.
    :return: A tuple (instance, created), where `instance` is the retrieved or created instance,
             and `created` is a boolean indicating whether the instance was created.
    """
    defaults = defaults or {}

    # Build a query to find an existing instance matching kwargs
    stmt = select(model).filter_by(**kwargs)
    instance = session.scalars(stmt).first()

    if instance:
        # Return the existing instance with `created` set to False
        return instance, False

    # Create a new instance if none was found
    try:
        instance = model(**{**kwargs, **defaults})
        session.add(instance)
        session.flush()  # Persist the new instance and assign primary key
        return instance, True
    except IntegrityError:
        # Handle potential race conditions in a multi-threaded or concurrent environment
        if session.in_transaction():
            if session.in_transaction():
                session.rollback()
        instance = session.scalars(stmt).first()
        return instance, False


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

    jumps = attr.split(".")
    for attr in jumps:
        obj = getattr(obj, attr)
    return sorted(obj, key=utils.natsort_key)


# from sqlalchemy.orm import aliased
def get_orm_entity_by_name(entity_name):
    """
    Dynamically resolve an ORM entity (class) from its name.

    Handles plural forms like `genera` by resolving relationships.

    :param entity_name: The name of the entity to resolve.
    :return: The ORM entity class or aliased entity if applicable.
    :raises ValueError: If the entity cannot be resolved.
    """
    from bauble.db import MapperBase  # Ensure you're using the correct base
    from sqlalchemy.orm import aliased

    # Normalize the entity name to lowercase for case-insensitive matching
    entity_name = entity_name.lower()

    # Check if the name exists directly in the class registry
    orm_entity = MapperBase._class_registry.get(entity_name)
    if orm_entity:
        return orm_entity

    # Handle plural cases dynamically
    if entity_name == "genera":
        genus_entity = MapperBase._class_registry.get("genus")
        if not genus_entity:
            raise ValueError("Genus not found in class registry")
        # Return aliased genus for queries
        return aliased(genus_entity)

    # Raise an error for unresolved names
    raise ValueError(f"Cannot resolve ORM entity for name: {entity_name}")


class MapperBase(DeclarativeMeta):
    """
    MapperBase adds the id, _created and _last_updated columns to all
    tables.  It also maintains a class registry for ORM-mapped classes.

    In general there is no reason to use this class directly other
    than to extend it to add more default columns to all the bauble
    tables.
    """

    id: Any
    _created: Any
    _last_updated: Any
    top_level_count: Any
    search_view_markup_pair: Any
    _class_registry: Any = {}

    def __init__(self, classname, bases, dict_) -> None:
        if "top_level_count" not in dict_:
            self.top_level_count = lambda x: {classname: 1}
        if "search_view_markup_pair" not in dict_:
            self.search_view_markup_pair = lambda x: (
                utils.xml_safe(str(x)),
                f"({type(x).__name__})",
            )

        # Add the class to the registry
        MapperBase._class_registry[classname.lower()] = self

        super().__init__(classname, bases, dict_)

        # Automatically add event listeners for insert, update, delete
        MapperBase._register_event_listeners(self)

    @staticmethod
    def add_history_entry(operation, instance, connection) -> None:
        """
        Helper function to add a history entry.

        This logs changes to the history table for a given operation
        (`insert`, `update`, or `delete`) on an ORM-mapped instance.
        """
        session = orm.object_session(instance)
        if not session:
            logger.warning("No session found for instance: %s", instance)
            return

        try:
            insp = inspect(instance)

            # PK after INSERT should be in identity; for DELETE it may be None
            pk = None
            if insp.identity is not None and len(insp.identity) > 0:
                pk = insp.identity[0]
            else:
                # fallback: direct attribute (may be None for DELETE or server-side PKs)
                pk = getattr(instance, "id", None)

            if pk is None:
                # For deletes or odd cases, either skip or relax the NOT NULL constraint.
                # We’ll skip to honor NOT NULL on history.table_id
                logger.warning(
                    "History: skipping %s for %s (no primary key available)",
                    operation, instance.__tablename__
                )
                return
            user = current_user() or "unknown"
            row = {
                c.name: utils.to_unicode(getattr(instance, c.name))
                for c in instance.__table__.columns
            }

            table = History.__table__
            stmt = table.insert().values(
                table_name=instance.__tablename__,
                #table_id=getattr(instance, "id", None),
                table_id=pk,
                values=str(row),
                operation=operation,
                user=user,
                timestamp=datetime.datetime.now(),
            )
            connection.execute(stmt)
            logger.debug("History entry added: %s", stmt)
        except Exception as e:
            logger.exception("History logging failed for %s on %s: %s",
                            operation, instance.__tablename__, e)


    @staticmethod
    def _register_event_listeners(cls) -> None:
        """
        Registers SQLAlchemy ORM event listeners for a mapped class.
        """

        @event.listens_for(cls, "after_insert")
        def after_insert(mapper, connection, target):
            logger.debug(f"Insert event for {target.__tablename__}")
            MapperBase.add_history_entry("insert", target, connection)

        @event.listens_for(cls, "after_update")
        def after_update(mapper, connection, target):
            logger.debug(f"Update event for {target.__tablename__}")
            MapperBase.add_history_entry("update", target, connection)

        @event.listens_for(cls, "after_delete")
        def after_delete(mapper, connection, target):
            logger.debug(f"Delete event for {target.__tablename__}")
            MapperBase.add_history_entry("delete", target, connection)


engine: Any = None
"""A :class:`sqlalchemy.engine.base.Engine` used as the default
connection to the database.
"""


from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import scoped_session

Session: scoped_session[SQLAlchemySession] = scoped_session(
    sessionmaker(autoflush=False, future=True)
)

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


class TypedBaseMixin:
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    _created: Mapped[datetime.datetime] = mapped_column(types.DateTime(), default=datetime.datetime.utcnow)
    _last_updated: Mapped[datetime.datetime] = mapped_column(types.DateTime(), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


    @classmethod
    def query_with_default_order(cls):
        """
        Return a query for the class with default ordering applied if defined.
        Works with SQLAlchemy 2.0.
        """
        stmt = select(cls)
        if hasattr(cls, "order_by") and cls.order_by:
            stmt = stmt.order_by(*cls.order_by)
        return stmt
    
Base: Any = declarative_base(cls=TypedBaseMixin, metaclass=MapperBase)
"""
All tables/mappers in Ghini which use the SQLAlchemy declarative
plugin for declaring tables and mappers should derive from this class.

An instance of :class:`sqlalchemy.orm.Base`
"""


metadata: Any = Base.metadata
"""The default metadata for all Ghini tables.

An instance of :class:`sqlalchemy.schema.Metadata`
"""

history_base: Any = declarative_base(metadata=metadata)


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

    __tablename__: str = "history"
    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    table_id: Mapped[int] = mapped_column(sa.Integer, nullable=False, autoincrement=False)
    values: Mapped[str] = mapped_column(sa.Text, nullable=False)
    operation: Mapped[str] = mapped_column(sa.Text, nullable=False)
    user: Mapped[Optional[str]] = mapped_column(sa.Text)
    timestamp: Mapped[datetime.datetime] = mapped_column(types.DateTime, nullable=False)



def open(uri, verify: bool = True, show_error_dialogs: bool = False):
    """
    Open a database connection. This function sets `bauble.db.engine` to
    the opened engine.

    Returns `bauble.db.engine` if successful, else returns None, and
    `bauble.db.engine` remains unchanged.

    :param uri: The URI of the database to open.
    :type uri: str
    :param verify: Whether the database we connect to should be verified
        as one created by Ghini. Mostly for testing.
    :type verify: bool
    :param show_error_dialogs: Whether to display error dialogs. Mostly for testing.
    :type show_error_dialogs: bool
    """
    logger.debug(f"db.open({uri})")
    import bauble.prefs
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.pool import NullPool, SingletonThreadPool

    # Create the SQLAlchemy engine
    try:
        poolclass = SingletonThreadPool if bauble.prefs.testing else NullPool

        connect_args = {}
        if "sqlite" in uri and bauble.prefs.testing:
            connect_args["timeout"] = 30  # SQLite supports this, PostgreSQL does not

        new_engine = sa.create_engine(
            uri,
            echo=SQLALCHEMY_DEBUG,
            poolclass=poolclass,
            future=True,  # Enable SQLAlchemy 2.0 features
            connect_args=connect_args,  # Add connect_args here
        )
        # TODO: there is a problem here: the code may cause an exception, but we
        # immediately loose the 'new_engine', which should know about the
        # encoding used in the exception string.
        new_engine.connect().close()  # Ensure connection can be established
    except SQLAlchemyError as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

    def _bind():
        """
        Bind the engine and configure the session factory.
        """
        global engine
        if engine is not None:
            engine.dispose()
        engine = new_engine
        metadata.bind = engine
        Session.remove()
        Session.configure(bind=engine, future=True)

    # Skip verification if not requested
    if not verify:
        _bind()
        return engine

    try:
        verify_connection(new_engine, show_error_dialogs)
    except Exception as e:
        _bind()
        logger.error(f"Database verification failed: {e}")
        raise
    else:
        _bind()

        return engine

# def create_triggers(connection) -> None:
#     """
#     Creates triggers for all TEXT columns in SQLite to convert empty strings to NULL.
#     Adds constraints in PostgreSQL to prevent empty strings.
#     """
#     inspector = inspect(connection)

#     if connection.engine.name == "sqlite":
#         logger.info("Creating SQLite triggers to normalize empty strings to NULL.")

#         # Loop through all tables
#         for table_name in inspector.get_table_names():
#             # Get column details
#             columns = inspector.get_columns(table_name)

#             for column in columns:
#                 col_name = column["name"]
#                 col_type = column["type"].__class__.__name__.lower()

#                 # Only apply triggers to TEXT columns
#                 if "text" in col_type or "varchar" in col_type:
#                     trigger_name = f"normalize_empty_strings_{table_name}_{col_name}"

#                     connection.execute(
#                         text(
#                             f"""
#                         CREATE TRIGGER IF NOT EXISTS {trigger_name}
#                         BEFORE INSERT OR UPDATE ON {table_name}
#                         FOR EACH ROW
#                         WHEN NEW.{col_name} = ''
#                         BEGIN
#                             UPDATE {table_name} SET {col_name} = NULL WHERE rowid = NEW.rowid;
#                         END;
#                     """
#                         )
#                     )

#         if connection.in_transaction():
#             connection.commit()

#     elif connection.engine.name == "postgresql":
#         logger.info("Adding PostgreSQL column constraints to prevent empty strings.")

#         for table_name in inspector.get_table_names():
#             columns = inspector.get_columns(table_name)

#             for column in columns:
#                 col_name = column["name"]
#                 col_type = column["type"].__class__.__name__.lower()

#                 if "text" in col_type or "varchar" in col_type:
#                     connection.execute(
#                         text(
#                             f"""
#                         ALTER TABLE {table_name} ALTER COLUMN {col_name} SET DEFAULT NULL;
#                     """
#                         )
#                     )

#         if connection.in_transaction():
#             connection.commit()


def _is_textual(col_type) -> bool:
    # inspector.get_columns() gives you SA types; handle common textual types
    return isinstance(col_type, (String, Text, Unicode, UnicodeText))


def _quote(preparer, name: str) -> str:
    # SQLAlchemy’s dialect preparer does correct quoting per backend
    return preparer.quote(name)


def _iter_user_tables_sqlite(inspector) -> Iterable[str]:
    # SQLite has no schemas; get all tables (skip sqlite internal tables just in case)
    for t in inspector.get_table_names():
        if not t.startswith("sqlite_"):
            return [t]
    return inspector.get_table_names()


def _iter_schemas_and_tables_pg(inspector) -> Iterable[tuple[str, str]]:
    # Walk non-system schemas
    for schema in inspector.get_schema_names():
        if schema in ("pg_catalog", "information_schema"):
            continue
        for t in inspector.get_table_names(schema=schema):
            yield schema, t


# def _col_preserves_empty(metadata, table_name: str, col_name: str) -> bool:
#     tbl = metadata.tables.get(table_name)
#     if not tbl:
#         return False
#     col = tbl.c.get(col_name)
#     return bool(getattr(col, "info", {}).get("preserve_empty"))


def _col_preserves_empty(metadata, table, column):
    """
    Return True if this column should *not* be normalized '' -> NULL.
    Keeps the original signature: (metadata, table, column).

    - `table` may be a table *name* (str) or a Table object
    - `column` may be an inspector column dict or a Column object
    """
    # Normalize table -> SA Table
    tbl = metadata.tables.get(table) if isinstance(table, str) else table
    if tbl is None:
        return False

    # Normalize column -> name
    if isinstance(column, dict):
        col_name = column.get("name")
    else:
        col_name = getattr(column, "name", None)
    if not col_name:
        return False

    # Get the mapped SA Column
    cols = getattr(tbl, "columns", getattr(tbl, "c", None))
    sa_col = cols.get(col_name) if hasattr(cols, "get") else None
    if sa_col is None:
        return False

    # 1) Our custom Enum with empty_to_none=False => preserve ''
    try:
        from bauble.btypes import Enum as BaubleEnum

        if isinstance(sa_col.type, BaubleEnum):
            return not getattr(sa_col.type, "empty_to_none", False)
    except Exception:
        pass

    # 2) Any CHECK constraint that explicitly allows '' => preserve ''
    from sqlalchemy import CheckConstraint

    for cons in getattr(tbl, "constraints", []):
        if isinstance(cons, CheckConstraint):
            sqltxt = str(cons.sqltext)
            if col_name in sqltxt and "''" in sqltxt:
                return True

    return False


def create_triggers(connection: Connection) -> None:
    """
    For SQLite: per-column AFTER triggers that normalize '' -> NULL.
    For PostgreSQL: per-table BEFORE triggers (INSERT, UPDATE OF ...) that set NEW.col := NULL for ''.
    """
    dialect = connection.dialect
    name = dialect.name
    inspector = inspect(connection)
    preparer = dialect.identifier_preparer

    if name == "sqlite":
        # SQLite cannot assign to NEW.*; use AFTER triggers and a single-row UPDATE keyed by rowid.
        for table in inspector.get_table_names():
            cols = inspector.get_columns(table)
            text_cols = [
                c for c in cols if _is_textual(c["type"]) and c.get("nullable", True)
            ]
            if not text_cols:
                continue

            qt = _quote(preparer, table)

            for c in text_cols:
                col = c["name"]

                if _col_preserves_empty(metadata, table, col):
                    continue

                qc = _quote(preparer, col)

                trig_ins = _quote(preparer, f"trg_norm_{table}_{col}_ins")
                trig_upd = _quote(preparer, f"trg_norm_{table}_{col}_upd")

                # AFTER INSERT: if NEW.col == '' then rewrite to NULL using a self-UPDATE on rowid
                sql_ins = f"""
                    CREATE TRIGGER IF NOT EXISTS {trig_ins}
                    AFTER INSERT ON {qt}
                    WHEN NEW.{qc} = ''
                    BEGIN
                        UPDATE {qt} SET {qc} = NULL WHERE rowid = NEW.rowid;
                    END;
                """

                # AFTER UPDATE OF col: if NEW.col == '' then rewrite to NULL
                sql_upd = f"""
                    CREATE TRIGGER IF NOT EXISTS {trig_upd}
                    AFTER UPDATE OF {qc} ON {qt}
                    WHEN NEW.{qc} = ''
                    BEGIN
                        UPDATE {qt} SET {qc} = NULL WHERE rowid = NEW.rowid;
                    END;
                """

                connection.execute(text(sql_ins))
                connection.execute(text(sql_upd))

        return  # done

    if name == "postgresql":
        # Build one function per table that normalizes all relevant columns,
        # then hook it up with BEFORE INSERT and BEFORE UPDATE OF <cols>.
        for schema, table in _iter_schemas_and_tables_pg(inspector):
            cols = inspector.get_columns(table, schema=schema)
            text_cols = [
                c for c in cols if _is_textual(c["type"]) and c.get("nullable", True)
            ]
            if not text_cols:
                continue

            # Qualified table name
            if schema:
                qt = f"{_quote(preparer, schema)}.{_quote(preparer, table)}"
            else:
                qt = _quote(preparer, table)

            # Function and trigger names live in the same schema as the table.
            fn_name = f"normalize_empty_{table}"
            qfn = (
                f"{_quote(preparer, schema)}.{_quote(preparer, fn_name)}"
                if schema
                else _quote(preparer, fn_name)
            )

            trig_ins = _quote(preparer, f"trg_norm_{table}_ins")
            trig_upd = _quote(preparer, f"trg_norm_{table}_upd")

            # Drop old triggers/functions if they exist (CREATE TRIGGER has no IF NOT EXISTS in PG).
            connection.execute(text(f"DROP TRIGGER IF EXISTS {trig_ins} ON {qt};"))
            connection.execute(text(f"DROP TRIGGER IF EXISTS {trig_upd} ON {qt};"))
            connection.execute(text(f"DROP FUNCTION IF EXISTS {qfn}() CASCADE;"))

            # Build function body: if NEW."col" = '' then NEW."col" := NULL;
            checks = "\n".join(
                f'    IF NEW.{_quote(preparer, c["name"])} = \'\' THEN NEW.{_quote(preparer, c["name"])} := NULL; END IF;'
                for c in text_cols
            )

            fn_sql = f"""
                CREATE FUNCTION {qfn}() RETURNS trigger AS $$
                BEGIN
{checks}
                  RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """
            connection.execute(text(fn_sql))

            # BEFORE INSERT always; BEFORE UPDATE only “OF” those columns
            col_list = ", ".join(_quote(preparer, c["name"]) for c in text_cols)

            trg_sql_ins = f"""
                CREATE TRIGGER {trig_ins}
                BEFORE INSERT ON {qt}
                FOR EACH ROW
                EXECUTE FUNCTION {qfn}();
            """
            trg_sql_upd = f"""
                CREATE TRIGGER {trig_upd}
                BEFORE UPDATE OF {col_list} ON {qt}
                FOR EACH ROW
                EXECUTE FUNCTION {qfn}();
            """
            connection.execute(text(trg_sql_ins))
            connection.execute(text(trg_sql_upd))

        return

    # Other backends: no-op (or you could add your own normalization here)

# --- Relationship wiring (idempotent) ---
_REL_WIRED = False

def ensure_relationships_wired() -> None:
    """
    Import all garden model modules, wire relationships, and finalize mappers.
    Safe to call multiple times.
    """
    global _REL_WIRED
    if _REL_WIRED:
        return

    import importlib
    import logging

    from sqlalchemy.orm import configure_mappers

    # Ensure all model classes are imported before wiring
    for mod in [
        "bauble.plugins.garden.models.accession",
        "bauble.plugins.garden.models.association_tables",
        "bauble.plugins.garden.models.contact",
        "bauble.plugins.garden.models.location",
        "bauble.plugins.garden.models.plant",
        "bauble.plugins.garden.models.plant_change",
        "bauble.plugins.garden.models.propagation",
        "bauble.plugins.garden.models.source",
        "bauble.plugins.garden.models.verification",
        "bauble.plugins.garden.models.voucher",
    ]:
        try:
            importlib.import_module(mod)
        except Exception as e:
            logger.debug("Skipping import %s: %s", mod, e)

    # Wire relationships once all classes exist
    import bauble.plugins.garden.models as garden_models
    garden_models.wire_relationships()

    # Finalize ORM mappings
    configure_mappers()
    _REL_WIRED = True

def create(import_defaults: bool = True) -> None:
    """
    Create a new Ghini database at the current connection.

    :param import_defaults: A flag that is passed to each plugin's
        `install()` method to indicate whether it should import its
        default data. Mainly used for testing. Default is True.
    :type import_defaults: bool
    """
    logger.debug("Entered db.create()")

    if not engine:
        raise ValueError("Engine is None. Not connected to a database.")

    import datetime

    import bauble
    import bauble.meta as meta
    from bauble import pluginmgr

    try:
        # 1) Load plugins so their models are imported and mapped classes exist
        pluginmgr.load()  # <— add this call

        from bauble.db import ensure_relationships_wired
        ensure_relationships_wired()

        with engine.begin() as connection:
            # Ensure all mappers are configured before creating tables
            import bauble.plugins.garden.models.accession as acc
            import bauble.plugins.garden.models.plant as pl
            from bauble.db import MapperBase, metadata
            from sqlalchemy.orm import configure_mappers

            print("accession in shared metadata? ", "accession" in metadata.tables)
            print(
                "Accession uses shared metadata? ",
                acc.Accession.__table__.metadata is metadata,
            )
            print(
                "Plant uses shared metadata? ", pl.Plant.__table__.metadata is metadata
            )
            print(
                "Mapped class names seen so far:",
                sorted(MapperBase._class_registry.keys()),
            )

            import inspect as pyinspect
            import sys

            import bauble.plugins.garden.models.accession as acc
            import bauble.plugins.garden.models.plant as pl
            from bauble.db import Base

            metadata = Base.metadata

            dbmod = sys.modules[__name__]  # since this code is running inside bauble.db
            print("db module path:", pyinspect.getfile(dbmod), "id:", id(dbmod))
            print(
                "Garden model modules loaded:",
                [k for k in sys.modules if "bauble.plugins.garden.models" in k],
            )

            print("db module path:", pyinspect.getfile(dbmod), "id:", id(dbmod))
            print("Accession Base is db.Base? ", acc.Base is dbmod.Base)
            # if plant.py still uses "from bauble.db import Base", this will exist:
            print("Plant module has 'db' alias? ", hasattr(pl, "db"))
            if hasattr(pl, "db"):
                print("pl.db is dbmod? ", pl.db is dbmod)

            print(
                "Accession uses shared metadata? ",
                acc.Accession.__table__.metadata is metadata,
            )
            print(
                "Plant uses shared metadata? ", pl.Plant.__table__.metadata is metadata
            )
            print("Tables in shared metadata:", sorted(metadata.tables.keys()))
            print("accession in shared metadata? ", "accession" in metadata.tables)
            print("plant in shared metadata? ", "plant" in metadata.tables)
            configure_mappers()

            # Drop and recreate all tables
            logger.debug("Dropping and recreating all tables.")
            metadata.drop_all(bind=connection, checkfirst=True)
            metadata.create_all(bind=connection)

            # 🛠️ Add triggers or column constraints for ALL TEXT columns
            create_triggers(connection)

            # Populate the Bauble meta table
            meta_table = meta.BaubleMeta.__table__

            # Insert VERSION_KEY
            logger.debug("Inserting version key.")
            version_stmt = insert(meta_table).values(
                name=meta.VERSION_KEY, value=str(bauble.version)
            )
            connection.execute(version_stmt)

            # Insert CREATED_KEY
            logger.debug("Inserting created timestamp.")
            import time

            tzlocal = datetime.timezone(-datetime.timedelta(seconds=time.timezone))
            created_stmt = insert(meta_table).values(
                name=meta.CREATED_KEY, value=str(datetime.datetime.now(tz=tzlocal))
            )
            connection.execute(created_stmt)

        # Install plugins
        try:
            logger.debug("Installing plugins.")
            pluginmgr.install("all", import_defaults, force=True)
        except Exception as e:
            logger.warning(f"Plugin installation failed: {e}")
            raise

        logger.info("Database created successfully.")

    except Exception as e:
        logger.error(f"Error while creating the database: {e}")
        raise


def verify_connection(engine, show_error_dialogs: bool = False):
    """
    Test whether a connection to an engine is a valid Ghini database.
    Raises an error for the first problem it finds with the database.

    :param engine: The engine to test.
    :type engine: sqlalchemy.engine.Engine
    :param show_error_dialogs: Flag to show error dialogs for issues. Default=False.
    :type show_error_dialogs: bool
    """
    logger.debug(f"Entered verify_connection(show_error_dialogs={show_error_dialogs})")
    import bauble
    import bauble.meta as meta

    def handle_error(error_cls, message, *args, **kwargs):
        """
        Raise an exception with message and additional arguments.
        Only show a dialog if enabled.
        """
        if show_error_dialogs:
            utils.message_dialog(message, Gtk.MessageType.ERROR)

        # Build exception, passing message first if accepted
        try:
            exc = error_cls(message, *args, **kwargs)
        except TypeError:
            # Fall back if message is not accepted in constructor
            exc = error_cls(*args, **kwargs)

        raise exc

    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        # Check if the database has any tables
        if not table_names:
            handle_error(error.EmptyDatabaseError, __("The database is empty."))

        # Check for the presence of the bauble meta table
        if meta.BaubleMeta.__tablename__ not in table_names:
            handle_error(
                error.MetaTableError,
                __(
                    "The database does not have the bauble meta table. "
                    "This may indicate a corrupt database or one created "
                    "with an incompatible version of Ghini."
                ),
            )

        # if we don't close this session before raising an exception then we
        # will probably get deadlocks....i'm not really sure why
        # Create a temporary session for schema validation
        from sqlalchemy.orm import sessionmaker

        with sessionmaker(bind=engine, autoflush=False, future=True)() as session:
            # Check for the presence of the "created" timestamp
            created_stmt = select(meta.BaubleMeta).where(
                meta.BaubleMeta.name == meta.CREATED_KEY
            )
            if not session.execute(created_stmt).scalar_one_or_none():
                handle_error(
                    error.TimestampError,
                    __(
                        "The database lacks a 'created' timestamp in the bauble meta table."
                        "This usually means that there was a problem when you created the "
                        "database or the database you connected to wasn't created with Ghini."
                    ),
                )

            # Check for the "version" key and validate compatibility
            version_stmt = select(meta.BaubleMeta).where(
                meta.BaubleMeta.name == meta.VERSION_KEY
            )
            version_row = session.execute(version_stmt).scalar_one_or_none()

            if not version_row:
                handle_error(
                    error.VersionError,
                    __("The database lacks a 'version' key in the bauble meta table."),
                    None,
                )

            try:
                major, minor, _ = map(int, version_row.value.split("."))
                if (str(major), str(minor)) != tuple(
                    map(str, bauble.version_tuple[:2])
                ):
                    handle_error(
                        error.VersionError,
                        __(
                            "You are using Ghini version %(version)s while the "
                            "database you have connected to was created with "
                            "version %(db_version)s\n\nSome things might not work as "
                            "or some of your data may become unexpectedly "
                            "corrupted."
                        )
                        % {"version": bauble.version, "db_version": version_row.value},
                        version_row.value,
                    )
            except ValueError:
                handle_error(
                    error.VersionError,
                    __("Invalid version format in the bauble meta table."),
                    version_row.value,
                )

        logger.info("Database connection successfully verified.")
        return True

    except Exception as e:
        logger.error(f"Error during database verification: {e}")
        raise


# def make_note_class(name, compute_serializable_fields=None, as_dict=None, retrieve=None):
def make_note_class(
    name,
    related_class,
    compute_serializable_fields: Optional[Any] = None,
    as_dict: Optional[Any] = None,
    retrieve: Optional[Any] = None,
):
    """
    Create a Note class with a relationship to the related_class using back_populates.

    :param name: The name of the related class (e.g., 'Genus', 'Species').
    :param related_class: The class to which the Note is related.
    :param compute_serializable_fields: Optional callable to compute serializable fields.
    :param as_dict: Optional callable to define how the object is serialized.
    :param retrieve: Optional callable to define how to retrieve the object.
    """
    from sqlalchemy import Integer

    class_name = f"{name}Note"
    table_name = f"{name.lower()}_note"

    def is_defined(self):
        return bool(self.user and self.category and self.note)

    def is_empty(self):
        return not self.user and not self.category and not self.note

    @classmethod
    def retrieve_or_create(cls, session, keys, create=True, update=True):
        """
        Retrieve or create a database object corresponding to keys.
        """
        original_category = keys.get("category", "")

        # Handle special cases for unique categories
        if create and (
            original_category.startswith("[")
            and original_category.endswith("]")
            or original_category == "<picture>"
        ):
            import uuid

            keys["category"] = str(uuid.uuid4())

        # Call the parent class's retrieve_or_create
        try:
            result = super(globals()[class_name], cls).retrieve_or_create(
                session, keys, create, update
            )
            keys["category"] = original_category
            if result:
                result.category = original_category
            return result
        except AttributeError as e:
            logger.error(f"Parent class does not implement retrieve_or_create: {e}")
            raise

    @classmethod
    def retrieve_default(cls, session, keys):
        """
        Retrieve a default instance of the class based on the provided keys.

        :param cls: The class type being queried.
        :param session: The SQLAlchemy session.
        :param keys: A dictionary of filtering criteria.
        :return: The instance if found, otherwise None.
        """

        try:
            # Start with a base query
            stmt = cls.query_with_default_order()

            # Filter by related object if given
            # Accept either the related object's code (common in your codebase)
            # or its id directly.
            if name.lower() in keys or "code" in keys or f"{name.lower()}_id" in keys:
                # Join to related_class if we need to filter by its code
                if "code" in keys or name.lower() in keys:
                    stmt = (
                        stmt.join(related_class, related_class.id == getattr(cls, f"{name.lower()}_id"))
                        .where(related_class.code == keys.get("code") or keys.get(name.lower()))
                    )
                elif f"{name.lower()}_id" in keys:
                    stmt = stmt.where(getattr(cls, f"{name.lower()}_id") == keys[f"{name.lower()}_id"])


            # Add filters for `date`
            if "date" in keys:
                stmt = stmt.where(cls.date == keys["date"])

            # Add filters for `category`
            if "category" in keys:
                stmt = stmt.where(cls.category == keys["category"])

            # Execute the query and fetch the result
            result = session.execute(stmt).scalars().one_or_none()

            return result

        except Exception as e:
            # Log the exception and return None
            logger.error(f"Error in retrieve_default for {cls.__name__}: {e}")
            return None

    # Default as_dict implementation
    def as_dict_default(self):
        result = Serializable.as_dict(self)
        result[name.lower()] = getattr(self, name.lower()).code
        return result

    as_dict = as_dict or as_dict_default
    retrieve = retrieve or retrieve_default

    bases = (Base,)
    fields = {
        "__tablename__": table_name,
        "id": mapped_column(Integer, primary_key=True, autoincrement=True),
        "date": mapped_column(types.DateTime, default=datetime.datetime.utcnow),
        "user": mapped_column(sa.Unicode(64), default=""),
        "category": mapped_column(sa.Unicode(32), default=""),
        "type": mapped_column(sa.Unicode(32), default=""),
        "note": mapped_column(sa.UnicodeText, nullable=False),
        name.lower() + "_id": mapped_column(
            sa.Integer, sa.ForeignKey(name.lower() + ".id"), nullable=False
        ),
        name.lower(): sa.orm.relationship(
            related_class.__name__,
            uselist=False,
            back_populates="notes",
            cascade="all, delete-orphan",
            single_parent=True,
            active_history=True,
        ),
        "retrieve": classmethod(retrieve),
        "retrieve_or_create": classmethod(retrieve_or_create),
        "is_defined": is_defined,
        "as_dict": as_dict,
    }
    if compute_serializable_fields is not None:
        bases = (Base, Serializable)
        fields["compute_serializable_fields"] = classmethod(compute_serializable_fields)

    result = type(class_name, bases, fields)
    result.order_by = [result.__table__.c.date.asc()]

    return result


class WithNotes:
    """
    A mixin to provide dynamic attribute access to notes based on categories.
    """

    key_pattern: Any = re.compile(r"{[^:]+:(.*)}")

    def __getattr__(self, name):
        """
        Retrieve a value from corresponding notes.

        The result can be:
        - An atomic value
        - A list of values
        - A dictionary

        :param name: The attribute name to retrieve.
        :return: The corresponding value(s) or raises AttributeError if not found.
        """
        # Ignore SQLAlchemy-related attributes
        if name.startswith("_sa"):
            raise AttributeError(name)

        result = []
        is_dict = False

        for note in self.notes:
            category = note.category
            note_text = note.note

            if category is None:
                continue

            if category == f"[{name}]":
                result.append(note_text)
            elif category.startswith(f"{{{name}:") and category.endswith("}"):
                is_dict = True
                match = self.key_pattern.match(category)
                if match:
                    key = match.group(1)
                    result.append((key, note_text))
            elif category == f"<{name}>":
                # Attempt to parse note text as JSON
                parsed_note = self._parse_json_safe(note_text)
                if parsed_note:
                    return parsed_note

        if not result:
            raise AttributeError(name)

        return dict(result) if is_dict else result

    @staticmethod
    def _parse_json_safe(text):
        """
        Parse text as JSON, fallback to the original text if parsing fails.

        Attempts parsing in two forms:
        - As a directly parsable JSON string.
        - As a normalized key-value format using `replace` and `re.sub`.

        :param text: The text to parse.
        :return: Parsed JSON object or the original text.
        """

        try:
            # Attempt parsing after normalizing the key-value structure
            normalized_text = re.sub(
                r"(\w+)[ ]*(?=:)", r'"\g<1>"', text.replace(";", ",")
            )
            return json.loads(normalized_text)
        except json.JSONDecodeError:
            pass

        try:
            normalized_text = re.sub(r"(\w+)[ ]*(?=:)", r'"\g<1>"', text)
            # Try parsing the text as-is
            return json.loads(normalized_text)
        except json.JSONDecodeError as e:
            logger.debug("JSON parsing failed: %s. Returning raw text: %s", e, text)
            return text




class DefiningPictures:
    @property
    def pictures(self):
        """
        Retrieve a list of Gtk.Image objects from notes with the "<picture>" category.

        :return: List of Gtk.Image objects.
        """
        result = []
        for note in self.notes:
            if note.category != "<picture>":
                continue
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)  # Updated for GTK 3.24+
            utils.ImageLoader(box, note.note).start()
            result.append(box)
        return result


class Serializable:
    """
    A base class for serializable ORM objects.
    """

    import re

    single_cap_re: Any = re.compile("([A-Z])")
    link_keys: Any = []

    def as_dict(self):
        """
        Convert the object to a dictionary representation.
        """
        result = {
            col: getattr(self, col)
            for col in list(self.__table__.columns.keys())
            if col not in ["id"]
            and col[0] != "_"
            and getattr(self, col) is not None
            and getattr(self, col) != ""
            and not col.endswith("_id")
        }
        result["object"] = self.single_cap_re.sub(
            r"_\1", self.__class__.__name__
        ).lower()[1:]
        return result

    @classmethod
    def correct_field_names(cls, keys) -> None:
        """
        Correct keys dictionary according to class attributes.

        Exchange format may use different keys than class attributes.
        """
        pass

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        """
        Create objects corresponding to keys (class dependent).

        :param session: The SQLAlchemy session.
        :param keys: A dictionary of keys for filtering or creation.
        :return: A dictionary of serializable fields.
        """
        return {}

    @classmethod
    def retrieve_or_create(
        cls, session, keys, create: bool = True, update: bool = True
    ):
        """
        Return a database object corresponding to keys, creating or updating as necessary.

        :param session: SQLAlchemy session
        :param keys: Dictionary of key-value pairs for lookup or creation
        :param create: Whether to create a new object if one doesn't exist
        :param update: Whether to update an existing object
        :return: The retrieved or created object
        """
        logger.debug("initial value of keys: %s", keys)

        # First attempt to retrieve the object
        is_in_session = cls.retrieve(session, keys)
        logger.debug("2 value of keys: %s", keys)

        if not create and not is_in_session:
            logger.debug("not creating from %s; returning None (1)", str(keys))
            return None

        if is_in_session and not update:
            logger.debug("returning not updated existing %s", is_in_session)
            return is_in_session

        try:
            # Compute any additional fields required for serialization
            extradict = cls.compute_serializable_fields(session, keys)
            cls.correct_field_names(keys)  # Correct field names
        except error.NoResultException:
            if not is_in_session:
                logger.debug("returning None (2)")
                return None
            else:
                extradict = {}
        except Exception:
            logger.exception("Unexpected error during serialization field computation")
            raise

        logger.debug("3 value of keys: %s", keys)

        # Parse timestamps in keys
        for timestamp_key in ["_created", "_last_updated"]:
            if timestamp_key in keys:
                keys[timestamp_key] = parse_date(keys[timestamp_key])

        logger.debug("3½ value of keys: %s", keys)

        # Handle linking keys (Python-side properties, not DB associations)
        link_values = {k: keys.pop(k) for k in cls.link_keys if k in keys}
        logger.debug("link_values: %s", link_values)

        # Remove keys that are not mapped columns or special cases
        mapped_columns = {col.key for col in class_mapper(cls).columns}
        keys = {k: v for k, v in keys.items() if k in mapped_columns}

        keys.update(extradict)  # Add extra computed fields
        logger.debug("4 value of keys: %s", keys)

        if not is_in_session and create:
            # Handle recursive creation of linked objects
            for key, link_value in link_values.items():
                if link_value:
                    logger.debug(
                        "Recursive call to construct_from_dict for %s", link_value
                    )
                    keys[key] = construct_from_dict(session, link_value)

            # Create a new object if it doesn't exist
            logger.debug("Creating new %s with %s", cls, keys)
            result = cls(**keys)
            session.add(result)
        elif is_in_session and update:
            result = is_in_session

            # Handle recursive updates of linked objects
            for key, link_value in link_values.items():
                if link_value:
                    logger.debug(
                        "Recursive call to construct_from_dict for %s", link_value
                    )
                    setattr(result, key, construct_from_dict(session, link_value))

            # Update fields on the existing object
            for k, v in keys.items():
                if isinstance(v, dict) and v.get("__class__") == "datetime":
                    millis = v.get("millis", 0)
                    v = datetime.datetime(1970, 1, 1) + datetime.timedelta(
                        milliseconds=millis
                    )
                setattr(result, k, v)

            logger.debug("Updated existing %s with %s", result, keys)

        # Ensure changes are flushed to the database
        session.flush()
        logger.debug("Returning %s", result)
        return result


def construct_from_dict(session, obj, create: bool = True, update: bool = True):
    """
    Construct an object from a dictionary representation.

    :param session: SQLAlchemy session.
    :param obj: Dictionary containing object data.
    :param create: Whether to create the object if it doesn't exist.
    :param update: Whether to update the object if it exists.
    :return: The constructed or retrieved object.
    """
    logger.debug("construct_from_dict %s", obj)

    klass = None

    # Determine the class of the object
    if "object" in obj:
        klass = class_of_object(obj["object"])
    if klass is None and "rank" in obj:
        klass_name = obj["rank"].capitalize()
        klass = globals().get(klass_name)
        del obj["rank"]  # Explicitly remove 'rank' after extracting its value

    if not klass:
        raise ValueError(f"Unable to determine class for object: {obj}")

    # Use the class's `retrieve_or_create` method to handle the object
    return klass.retrieve_or_create(session, obj, create=create, update=update)


def class_of_object(obj_name):
    """
    Determine the class that implements the object.

    :param obj_name: Name of the object.
    :return: The class that implements the object.
    """
    class_name = "".join(part.capitalize() for part in obj_name.split("_"))
    cls = globals().get(class_name)

    if cls is None:
        from bauble import pluginmgr

        cls = pluginmgr.provided.get(class_name)

    if not cls:
        raise ValueError(f"Class not found for object: {obj_name}")

    return cls


class current_user_functor:
    """
    Implement the current_user function and allow overriding.

    This is designed to return the current user's name from the database
    or the system, with support for overriding.
    """

    override_value: Any

    def __init__(self) -> None:
        self.override_value = None

    def override(self, value: Optional[Any] = None) -> None:
        """
        Override the current user value.

        :param value: The username to override with. If None, reset the override.
        """
        self.override_value = value

    def __call__(self):
        """
        Retrieve the current user name from the database or system.

        :return: The current user name.
        """
        if self.override_value:
            return self.override_value

        try:
            stmt = None
            if engine.name.startswith("postgresql"):
                stmt = sa.text("SELECT current_user")
            elif engine.name.startswith("mysql"):
                stmt = sa.text("SELECT current_user()")
            else:
                raise TypeError("Unsupported database engine for user retrieval.")

            with engine.connect() as conn:
                return conn.execute(stmt).scalar_one_or_none()
        except Exception:
            logger.debug("Falling back to system environment for user name retrieval.")
            return (
                os.getenv("USER")
                or os.getenv("USERNAME")
                or os.getenv("LOGNAME")
                or os.getenv("LNAME")
            )


# Instantiate the current_user function
current_user: Any = current_user_functor()


# --- Lazy re-exports for plugin models (so users can `from bauble.db import Family`) ---
import importlib

_EXPORTS = {
    # garden models
    "Accession": "bauble.plugins.garden.models.accession",
    "AccessionNote": "bauble.plugins.garden.models.accession",
    "Plant": "bauble.plugins.garden.models.plant",
    "PlantNote": "bauble.plugins.garden.models.plant",
    "Location": "bauble.plugins.garden.models.location",
    # plants models
    "Family": "bauble.plugins.plants.family",
    "Genus": "bauble.plugins.plants.genus",
    "Species": "bauble.plugins.plants.species_model",
    "SpeciesNote": "bauble.plugins.plants.species_model",
    "VernacularName": "bauble.plugins.plants.species_model",
    # add others you previously monkey-patched
}


def __getattr__(name):
    modpath = _EXPORTS.get(name)
    if not modpath:
        raise AttributeError(name)
    mod = importlib.import_module(modpath)
    obj = getattr(mod, name)
    # cache on bauble.db for future direct access
    globals()[name] = obj
    return obj
    mod = importlib.import_module(modpath)
    obj = getattr(mod, name)
    # cache on bauble.db for future direct access
    globals()[name] = obj
    return obj
