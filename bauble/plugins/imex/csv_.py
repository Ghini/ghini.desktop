#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
#
# csv import/export
#
# Description: have to name this module csv_ in order to avoid conflict
# with the system csv module
#
import csv
import logging
import os
import traceback
from collections.abc import Generator
from gettext import gettext as _
from inspect import signature
from queue import Queue
from typing import Any, Optional

import bauble.db as db
import bauble.pluginmgr as pluginmgr
import bauble.task
import bauble.utils as utils
from bauble import pb_set_fraction
from bauble.error import BaubleError
from bauble.gtkinit import GLib, Gtk
from bauble.plugins.imex.csv_processor import CSVProcessor
from bauble.plugins.imex.unicode_utils import UnicodeWriter

# from sqlalchemy import Boolean
from sqlalchemy import ColumnDefault, inspect
from sqlalchemy.exc import IntegrityError

# from sqlalchemy.exc import DataError
from sqlalchemy.orm import configure_mappers, sessionmaker

logger: Any = logging.getLogger(__name__)
QUOTE_STYLE: Any = csv.QUOTE_MINIMAL
QUOTE_CHAR: str = '"'
WRITE_IMPORT_SCHEMA_ENV = "GHINI_WRITE_IMPORT_SCHEMA"

# TODO: i've also had a problem with bad insert statements, e.g. importing a
# geography table after creating a new database and it doesn't use the
# 'name' column in the insert so there is an error, if  you then import the
# same table immediately after then everything seems to work fine

# TODO: should check that if we're dropping a table because of a
# dependency that we expect that data to be imported in this same
# task, or at least let the user know that the table is empty

# TODO: don't ask if we want to drop empty tables
# https://bugs.launchpad.net/bauble/+bug/103923

# TODO: allow the user set the unicode encoding on import, exports should
# always us UTF-8, import, exports should always use UTF-8, need to figure
# out how to extend the file open dialog,
# http://evanjones.ca/python-utf8.html
# import codecs
# fileObj = codecs.open( "someFile", "r", "utf-8" )
# u = fileObj.read() # Returns a Unicode string from the UTF-8 bytes in
# the file

# TODO: what happens when you export from one database type and try
# and import into a different database, e.g. postgres->sqlite
# bauble/plugins/imex/csv_.py

from typing import Any, Dict, List

import sqlalchemy as sa

# bauble/plugins/imex/csv_.py

def write_import_schema_markdown(metadata, out_path: str = "IMPORT_SCHEMA.md") -> str:
    """
    Emit a Markdown file that documents expected CSV columns/types/NULL rules.
    Safe for enum values that include None and other non-str entries.
    """
    schema = describe_metadata(metadata)

    def _s(v):
        # stringify for markdown; handle None and callables nicely
        if v is None:
            return "None"
        try:
            return str(v)
        except Exception:
            return repr(v)

    def _pipe_escape(v: str) -> str:
        # very light escaping so '|' in values doesn't break the table
        return v.replace("|", r"\|")

    lines: list[str] = []
    lines.append("# Ghini CSV Import Schema")
    lines.append("")
    lines.append("> Generated from SQLAlchemy metadata; reflects the source of truth.")
    lines.append("")

    for table, cols in schema.items():
        lines.append(f"## Table `{table}`")
        lines.append("")
        lines.append("| Column | Type | Nullable | Default | PK | Unique | FK | Enum Values | empty_to_none | strict |")
        lines.append("|---|---|:---:|---|:--:|:--:|---|---|:--:|:--:|")

        for c in cols:
            enum_vals = ""
            if c.get("enum_values"):
                # stringify each entry, including None
                enum_vals = ", ".join(_s(x) for x in c["enum_values"])

            row = [
                f"`{c['name']}`",
                _pipe_escape(_s(c['type'])),
                "Yes" if c.get("nullable") else "No",
                _pipe_escape(_s(c.get("default"))),
                "✓" if c.get("primary_key") else "",
                "✓" if c.get("unique") else "",
                _pipe_escape(_s(c.get("foreign_key") or "")),
                _pipe_escape(enum_vals),
                _s(c.get("enum_empty_to_none")) if c.get("enum_empty_to_none") is not None else "",
                _s(c.get("enum_strict")) if c.get("enum_strict") is not None else "",
            ]
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")
        lines.append("> **CSV expectations**")
        lines.append("> - Header row should include the column names you plan to supply.")
        lines.append("> - Missing headers fall back to Python-side defaults if defined; otherwise the column will be NULL (if allowed) or cause an error.")
        lines.append("> - Empty fields: see `Nullable` and Enum `empty_to_none` above.")
        lines.append("")

        # quick hint for likely problem columns
        nonnullable_text = [
            c["name"] for c in cols
            if not c.get("nullable")
            and c.get("type") in ("Unicode", "String", "Text")
        ]
        if nonnullable_text:
            lines.append("> **Non-nullable text columns** that must be provided (or coerced to ''):")
            lines.append("> " + ", ".join(f"`{n}`" for n in nonnullable_text))
            lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("Wrote import schema doc to %s", out_path)
    return out_path


def should_write_import_schema() -> bool:
    return os.environ.get(WRITE_IMPORT_SCHEMA_ENV, "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def describe_metadata(metadata) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build a structured description of the DB schema from SQLAlchemy MetaData.
    Returns:
      {table_name: [
         {name, type, nullable, default, primary_key, unique, foreign_key, enum_values, enum_empty_to_none, enum_strict}
      ]}
    """
    schema: Dict[str, List[Dict[str, Any]]] = {}
    for table in metadata.sorted_tables:
        cols = []
        for col in table.c:
            info: Dict[str, Any] = {
                "name": col.name,
                "type": type(col.type).__name__,
                "nullable": col.nullable,
                "primary_key": col.primary_key,
                "unique": bool(col.unique),
                "default": None,
                "foreign_key": None,
                "enum_values": None,
                "enum_empty_to_none": None,
                "enum_strict": None,
            }
            # default (Python-side)
            if col.default is not None:
                try:
                    from sqlalchemy import ColumnDefault
                    if isinstance(col.default, ColumnDefault):
                        info["default"] = getattr(col.default.arg, "__name__", col.default.arg)
                    else:
                        info["default"] = col.default
                except Exception:
                    info["default"] = str(col.default)

            # foreign key (first one, if any)
            if col.foreign_keys:
                fk = next(iter(col.foreign_keys))
                info["foreign_key"] = f"{fk.column.table.name}.{fk.column.name}"

            # Enums (SQLAlchemy or Bauble)
            try:
                from bauble.btypes import Enum as BaubleEnum
            except Exception:
                BaubleEnum = None  # type: ignore

            if isinstance(col.type, sa.Enum):
                info["enum_values"] = list(getattr(col.type, "enums", []) or [])
            elif BaubleEnum and isinstance(col.type, BaubleEnum):
                info["enum_values"] = list(getattr(col.type, "values", []) or [])
                info["enum_empty_to_none"] = getattr(col.type, "empty_to_none", None)
                info["enum_strict"] = getattr(col.type, "strict", None)

            cols.append(info)
        schema[table.name] = cols
    return schema


class Importer:

    def start(self, *args, **kwargs):
        """
        start the import process, this is a non blocking method, queue the
        process as a bauble task
        """
        gen = self.run(*args, **kwargs)

        return bauble.task.queue(gen)

    def run(self, **kwargs) -> None:
        """
        where all the action happens
        """
        raise NotImplementedError


class CSVImporter(Importer):
    """imports comma separated value files into a Ghini database.

    It imports multiple files, each of them equally named as the bauble
    database tables. The bauble tables dependency graph defines the correct
    import order, each file being imported will completely replace any
    existing data in the corresponding table.

    The CSVImporter imports the rows of the CSV file in chunks rather than
    one row at a time.  The non-server side column defaults are determined
    before the INSERT statement is generated instead of getting new defaults
    for each row.  This shouldn't be a problem but it also means that your
    column default should change depending on the value of previously
    inserted rows.

    """

    __error: bool
    __cancel: bool
    __pause: bool
    __error_exc: bool
    q: Any
    job_done: Any
    flush_count: int
    steps_so_far: int

    def __init__(self) -> None:
        super().__init__()
        self.__error = False  # flag to indicate error on import
        self.__cancel = False  # flag to cancel importing
        self.__pause = False  # flag to pause importing
        self.__error_exc = False
        self.q = Queue()  # Producer-Consumer Queue
        self.job_done = object()  # Sentinel for completion
        self.flush_count = 0

    def start(
        self,
        filenames: Optional[Any] = None,
        metadata: Optional[Any] = None,
        force: bool = False,
    ) -> None:
        """start the import process. this is a non blocking method: we queue
        the process as a bauble task. there is no callback informing whether
        it is successfully completed or not.

        """
        if metadata is None:
            metadata = db.metadata  # use the default metadata
            configure_mappers()

        if filenames is None:
            filenames = self._get_filenames()
        if filenames is None:
            return

        super().start(filenames, metadata, force)

    def _map_filenames_to_tables(self, filenames):
        """
        Create a mapping of table names to filenames.

        - Ensures that each table has only one corresponding file.
        - Displays an error if multiple files map to the same table.
        - Displays a warning if filenames do not match any known table.

        :param filenames: List of file paths.
        :return: Dictionary mapping table names to file paths.
        :raises ValueError: If there are duplicate filenames for a table.
        """
        filename_dict = {}

        # Extract table names from filenames
        for f in filenames:
            path, base = os.path.split(f)
            table_name, ext = os.path.splitext(base)

            if table_name in filename_dict:
                # Show an error message before raising an exception
                safe = utils.xml_safe
                values = {
                    "table_name": safe(table_name),
                    "file_name": safe(filename_dict[table_name]),
                    "file_name2": safe(f),
                }
                msg = (
                    _(
                        "More than one file given to import into table "
                        "<b>%(table_name)s</b>: %(file_name)s, %(file_name2)s"
                    )
                    % values
                )

                raise ValueError(msg)

            filename_dict[table_name] = f

        return filename_dict  # No sorting, since `run` already does it

    def _calculate_total_lines(self, filenames):
        """
        Calculate the total number of lines across all files and their individual sizes.

        :param filenames: List of file paths.
        :return: Tuple (total_lines, filesizes)
                 - total_lines: Total number of lines across all files.
                 - filesizes: Dictionary mapping filenames to line counts.
        :raises OSError: If a file cannot be read.
        """
        total_lines = 0
        filesizes = {}
        for filename in filenames:
            try:
                with open(filename) as file:
                    nlines = len(file.readlines())
                    filesizes[filename] = nlines
                    total_lines += nlines
            except OSError as e:
                raise OSError(_("Failed to read file: %s") % filename) from e
        return total_lines, filesizes

    def _handle_dependencies(self, sorted_tables, metadata, session, force):
        """
        Handle dependencies for the tables to be imported.
        Drops dependent tables if necessary.

        :param sorted_tables: List of (table, filename) tuples sorted by dependency.
        :param metadata: SQLAlchemy metadata object.
        :param session: SQLAlchemy session object.
        :param force: Boolean indicating whether to force dropping tables.
        :return: Set of dependent tables.
        :raises ValueError: If user declines to drop required tables.
        """
        depends = set()
        for table, _unused_var in sorted_tables:
            if self.__cancel or self.__error:
                break
            logger.debug(f"Get dependencies for table {table.name}")
            dependent_tables = utils.find_dependent_tables(table)
            logger.debug(
                f"Dependencies for {table.name}: {', '.join([t.name for t in dependent_tables])}"
            )
            depends.update(dependent_tables)

        if depends:
            response = True
            dependent_table_names = ", ".join(sorted([t.name for t in depends]))
            if not force:
                msg = (
                    _(
                        "In order to import the files, the following "
                        "tables will be dropped:\n\n<b>%s</b>\n\n"
                        "Would you like to continue?"
                    )
                    % dependent_table_names
                )
                force = response = utils.yes_no_dialog(msg)

            if not response:
                raise ValueError(_("Operation canceled by user."))

            try:
                logger.debug(f"Dropping tables: {dependent_table_names}")
                configure_mappers()
                # Drop all dependent tables, ensuring proper order
                sorted_depends = [t for t in metadata.sorted_tables if t in depends]
                metadata.drop_all(bind=session.get_bind(), tables=sorted_depends)

                logger.debug("Successfully dropped dependent tables.")
            except Exception as e:
                logger.error(f"Failed to drop dependent tables: {e}")
                raise

        return depends

    @staticmethod
    def _precompute_defaults(table):
        """
        Precompute only constants or zero-arg callables.
        Context-dependent defaults are left for SQLAlchemy to handle
        (by omitting the column in the row dict).
        """
        defaults = {}
        for column in table.c:
            coldef = column.default
            if not coldef or not isinstance(coldef, ColumnDefault):
                continue

            arg = coldef.arg

            # Literal constant default
            if not callable(arg):
                defaults[column.name] = arg
                continue

            # Callable default: only keep it if it’s invocable with zero args.
            # Some builtins (like datetime.utcnow) have no inspectable signature,
            # so just try calling with no args and detect TypeError.
            try:
                defaults[column.name] = arg()
            except TypeError:
                # requires ctx or args → skip; let SA apply it at INSERT time
                continue
            except Exception:
                # anything else weird → skip to be safe
                continue

        return defaults

    def _prepare_table(
        self, table, filename, filesizes, created_tables, depends, session, force
    ):
        """
        Handle table creation and management of empty files.

        :param table: Table object to prepare.
        :param filename: The CSV file corresponding to the table.
        :param filesizes: Dictionary of file sizes.
        :param created_tables: List of already created tables.
        :param depends: Set of dependent tables.
        :param session: SQLAlchemy session.
        :param force: Whether to force table recreation.
        :return: Boolean indicating if the table is ready for import.
        """
        # Check for cancellation or error before proceeding
        if self.__cancel or self.__error:
            return False

        # don't do anything if the file is empty:
        if filesizes[filename] <= 1:  # Handle empty files
            if table.name not in inspect(session.bind).get_table_names():
                self._create_table(table, session, created_tables)
            return False

        # check if the table was in the depends because they
        # could have been dropped whereas table.exists() can
        # return true for a dropped table if the transaction
        # hasn't been committed
        if (
            table in depends
            or table.name not in inspect(session.bind).get_table_names()
        ):
            logger.info(f"{table.name} does not exist. creating.")
            self._create_table(table, session, created_tables)
        elif table.name not in created_tables and table not in depends:
            # we get here if the table wasn't previously
            # dropped because it was a dependency of another
            # table
            if not force:
                msg = (
                    _(
                        "The <b>%s</b> table already exists in the "
                        "database and may contain some data. If a "
                        "row the import file has the same id as a "
                        "row in the database then the file will not "
                        "import correctly.\n\n<i>Would you like to "
                        "drop the table in the database first. You "
                        "will lose the data in your database if you "
                        "do this?</i>"
                    )
                    % table.name
                )
                if not utils.yes_no_dialog(msg):
                    return False
            table.drop(bind=session.bind)
            self._create_table(table, session, created_tables)
        return True

    def _create_table(self, table, session, created_tables) -> None:
        """
        Create a table using the session's bind.

        :param table: Table to create.
        :param session: SQLAlchemy session.
        :param created_tables: List of created tables.
        """
        configure_mappers()
        #        print(str(table.compile(bind=session.bind)))
        #        print([fk.column for fk in table.foreign_keys])
        table.create(bind=session.bind)
        if table.name not in created_tables:
            created_tables.append(table.name)

    # Ensure this is set up in your database initialization code
    Session: Any = sessionmaker(bind=db.engine, future=True)

    # Instead of recreating all tables, check for and create only missing ones
    def create_missing_tables(self, metadata, session) -> None:
        """
        Create missing tables in the correct order, respecting dependencies.

        :param metadata: SQLAlchemy metadata object.
        :param session: SQLAlchemy session object.
        """
        # Inspect existing tables
        inspector = inspect(session.bind)
        existing_tables = set(inspector.get_table_names())

        # Ensure tables are created in dependency order
        for table in metadata.sorted_tables:
            if table.name not in existing_tables:
                logger.info(f"Creating missing table: {table.name}")
                try:
                    table.create(bind=session.bind)
                    existing_tables.add(table.name)
                except Exception as e:
                    logger.error(f"Error creating table {table.name}: {e}")
                    raise

    def run(
        self, filenames, metadata, force: bool = False, _ctx=None
    ) -> Generator[None, None, None]:
        """
        A generator method for importing filenames into the database.
        This method periodically yields control so that the GUI can
        update.

        :param filenames:
        :param metadata:
        :param force: default=False
        """
        import logging

        logging.basicConfig()
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        self.flush_count = 0

        self.__error_exc = BaubleError(_("Unknown Error."))

        try:
            # Create a new session bound to the database engine
            with db.Session() as session:
                with session.begin():

                    configure_mappers()  # Ensure mappers are configured

                    # Map filenames to table names
                    try:
                        filename_dict = self._map_filenames_to_tables(filenames)
                    except ValueError as e:
                        utils.message_dialog(e, Gtk.MessageType.ERROR)
                        return

                    # resolve filenames to table names and return them in sorted order
                    sorted_tables = []
                    for table in metadata.sorted_tables:
                        try:
                            sorted_tables.insert(
                                0, (table, filename_dict.pop(table.name))
                            )
                        except KeyError:
                            # table.name not in list of filenames
                            pass

                    if should_write_import_schema():
                        try:
                            write_import_schema_markdown(metadata)
                        except Exception as _e:
                            logger.debug("Could not write IMPORT_SCHEMA.md: %s", _e)

                    if len(filename_dict) > 0:
                        msg = (
                            _("Could not match all filenames to table names.\n\n%s")
                            % filename_dict
                        )
                        utils.message_dialog(msg, Gtk.MessageType.ERROR)
                        return

                    # Calculate total lines and filesizes
                    try:
                        total_lines, filesizes = self._calculate_total_lines(filenames)
                    except OSError as e:
                        msg = _("Error reading files.\n\n%s") % utils.xml_safe(e)
                        utils.message_dialog(msg, Gtk.MessageType.ERROR)
                        return

                    created_tables = []

                    self.steps_so_far = 0

                    # Fetch and handle dependencies
                    try:
                        depends = self._handle_dependencies(
                            sorted_tables, metadata, session, force
                        )
                    except ValueError as e:
                        utils.message_dialog(str(e), Gtk.MessageType.ERROR)
                        return
            # Phase 2: import each file/table
            # NOTE: progress bar math is done here, mimicking the old 'do_insert()' path.
            processed = 0  # lines processed across all files (for progress numerator)
            # Old flow counted headers in total_lines; keep that for identical behavior.
            effective_total = max(total_lines, 1)

            # import the tables one at a time, breaking every so often
            # so the GUI can update
            for table, filename in reversed(sorted_tables):
                if self.__cancel or self.__error:
                    break

                msg = _("importing %(table)s table from %(filename)s") % {
                    "table": table.name,
                    "filename": filename,
                }
                logger.info(msg)
                bauble.task.set_message(msg)
                yield  # allow progress bar update

                with db.Session() as session:
                    try:

                        # Prepare the table and file
                        if not self._prepare_table(
                            table,
                            filename,
                            filesizes,
                            created_tables,
                            depends,
                            session,
                            force,
                        ):
                            continue

                        # precompute the defaults...this assumes that the
                        # default function doesn't depend on state after each
                        # row...it shouldn't anyways since we do an insert
                        # many instead of each row at a time
                        # Precompute the defaults for the table
                        defaults = self._precompute_defaults(table)

                        # update_every determines how many rows we will insert at
                        # a time and consequently how often we update the gui
                        processor = CSVProcessor(
                            table,
                            filename,
                            defaults,
                            update_every=127,
                            flush_count=self.flush_count,
                            steps_so_far=self.steps_so_far,
                            use_thread=False
                        )

                        from bauble.plugins.imex.csv_processor import (
                            preflight_csv as preflight_csv,
                        )
                        issues = preflight_csv(filename, table)
                        if issues["missing_headers"] or issues["empty_required_cells"] or issues["enum_violations"]:
                            # Log or show a dialog with a concise summary
                            logger.warning("Preflight for %s: %r", table.name, issues)
                            # Optionally abort early to let the user decide how to handle '' vs NULL

                        # Prepare the file for import and get column keys
                        processor.prepare_file()

                        processed_in_file = 0
                        last_steps = 0
                        for steps in processor.process_rows():
                            # CSVProcessor yields a cumulative "steps so far" for THIS FILE.
                            delta = max(steps - last_steps, 0)
                            last_steps = steps

                            processed += delta

                            # Keep progress strictly < 1.0 until the very end (old behavior).
                            frac = processed / effective_total
                            GLib.idle_add(pb_set_fraction, min(frac, 0.999))

                            yield

                        # Count rows in the table
                        # row_count = session.execute(sa.select(func.count()).select_from(table)).scalar_one()
                        # logger.debug(f"{table.name}: {row_count}")

                        # we have commit after create after each table is imported
                        # or Postgres will complain if two tables that are
                        # being imported have a foreign key relationship.
                        # The commit/rollback is handled automatically when we leave the
                        # 'with' block.


                        # Important: Cleanup after processing each table
                        processor.cleanup()
                        # Surface any insert error captured in the processor (covers sync mode too)
                        if getattr(processor, "worker_error", None) is not None:
                            raise RuntimeError(
                                f"Insert failed for table {table.name}"
                            ) from processor.worker_error

                        try:
                            import sqlalchemy as sa
                            rc = session.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()
                            logger.info("Imported %s rows into %s", rc, table.name)
                        except Exception:
                            logger.debug("Could not count rows for %s", table.name)
                                                    
                        session.commit()
                        logger.info(f"Successfully imported table: {table.name}")

                    except IntegrityError as e:
                        logger.error(f"Constraint violation in table {table.name}: {e}")
                        if session.in_transaction():
                            if session.in_transaction():
                                session.rollback()  # Rollback to prevent partial imports
                        utils.message_dialog(
                            _("Data import failed due to integrity constraints."),
                            Gtk.MessageType.ERROR,
                        )
                        self.__error = True
                        return
                    except Exception as e:
                        logger.error(f"Error processing table {table.name}: {e}")
                        if session.in_transaction():
                            if session.in_transaction():
                                session.rollback()
                        raise

                    # Update the GUI
                    self._update_gui()

            with db.Session() as session:

                # TODO: need to get those tables from depends that need to
                # be created but weren't created already
                # Ensure only missing tables are created
                self.create_missing_tables(metadata, session)

                # Reset sequences
                self._reset_sequences(sorted_tables)

                # Update the GUI
                self._update_gui()

            # Finally set the bar to 100%.
            GLib.idle_add(pb_set_fraction, 1.0)
        except Exception as e:
            msg = _("Error during import process.\n\n%s") % utils.xml_safe(e)
            utils.message_dialog(msg, Gtk.MessageType.ERROR)

            logger.error(e)
            logger.error(traceback.format_exc())
            self.__error = True
            self.__error_exc = e
            raise

    def _reset_sequences(self, sorted_tables) -> None:
        """
        Reset database sequences for all columns in the given tables.

        :param sorted_tables: List of (table, filename) tuples.
        """
        # unfortunately inserting an explicit value into a column that
        # has a sequence doesn't update the sequence, we shortcut this
        # by setting the sequence manually to the max(column)+1
        try:
            for table, _unused_var in sorted_tables:
                for column in table.c:
                    try:
                        utils.reset_sequence(column)
                    except Exception as e:
                        logger.error(
                            f"Failed to reset sequence for column {column.name} in table {table.name}: {e}"
                        )
                        raise
        except Exception:
            col_name = column.name if "column" in locals() else "Unknown"
            msg = _("Error: Could not set the sequence for column: %s") % col_name
            logger.error(msg)
            logger.debug(traceback.format_exc())
            utils.message_details_dialog(
                utils.xml_safe(msg),
                traceback.format_exc(),
                type=Gtk.MessageType.ERROR,
            )

    def _update_gui(self) -> None:
        """
        Update the GUI after processing.
        Logs an error if the update fails.
        """
        try:
            from bauble import gui

            if gui is not None:
                gui.get_view().update()
        except ImportError as e:
            logger.warning(f"GUI module import failed: {e}")
        except Exception as e:
            logger.error(f"Failed to update GUI: {e}")

    def _get_filenames(self):
        def on_selection_changed(filechooser, data=None):
            """
            only make the ok button sensitive if the selection is a file
            """
            f = filechooser.get_preview_filename()
            if f is None:
                return
            ok = filechooser.action_area.get_children()[1]
            ok.set_sensitive(os.path.isfile(f))

        fc = Gtk.FileChooserDialog(
            _("Choose file(s) to import…"),
            self,
            Gtk.FileChooserAction.OPEN,
            (
                Gtk.STOCK_OK,
                Gtk.ResponseType.ACCEPT,
                Gtk.STOCK_CANCEL,
                Gtk.ResponseType.REJECT,
            ),
        )
        fc.set_select_multiple(True)
        fc.connect("selection-changed", on_selection_changed)
        filenames = None
        if fc.run() == Gtk.ResponseType.ACCEPT:
            filenames = fc.get_filenames()
        fc.destroy()
        return filenames

    def on_response(self, widget, response, data: Optional[Any] = None) -> None:
        logger.debug("on_response")
        logger.debug(response)


from contextlib import contextmanager

from sqlalchemy import select


@contextmanager
def open_file_safe(filename, mode: str = "w") -> Generator[Any, None, None]:
    """Context manager for opening a file safely."""
    try:
        f = open(filename, mode)
        yield f
    finally:
        f.close()


class CSVExporter:

    steps_so_far: int

    def start(self, path: Optional[Any] = None) -> None:
        if path is None:
            d = Gtk.FileChooserDialog(
                _("Select a directory"),
                self,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (
                    Gtk.STOCK_OK,
                    Gtk.ResponseType.ACCEPT,
                    Gtk.STOCK_CANCEL,
                    Gtk.ResponseType.CANCEL,
                ),
            )
            response = d.run()
            path = d.get_filename()
            d.destroy()
            if response != Gtk.ResponseType.ACCEPT:
                return

        if not os.path.exists(path):
            raise ValueError(_("CSVExporter: path does not exist.\n%s") % path)

        try:
            # TODO: should we support exporting other metadata
            # besides db.metadata
            bauble.task.queue(self.__export_task(path))
        except Exception as e:
            logger.debug(f"{type(e).__name__}({e})")

    def __export_task(self, path) -> Generator[None, None, Any]:
        filename_template = os.path.join(path, "%s.txt")
        self.steps_so_far = 0
        ntables = 0

        # Count the number of tables
        for table in db.metadata.sorted_tables:
            ntables += 1
            filename = filename_template % table.name
            if os.path.exists(filename):
                msg = _(
                    "Export file <b>%(filename)s</b> for "
                    "<b>%(table)s</b> table already exists.\n\n<i>Would "
                    "you like to continue?</i>"
                ) % {"filename": filename, "table": table.name}
                if not utils.yes_no_dialog(msg):  # if NO: return
                    return

        def replace(s):
            if isinstance(s, str):
                s.replace("\n", "\\n")
            return s

        def write_csv(filename, rows):
            with open_file_safe(filename, "w") as f:
                writer = UnicodeWriter(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
                writer.writerows(rows)

        update_every = 30
        # spinner = '⣀⡄⠆⠃⠉⠘⠰⢠'
        spinner = "⡆⠇⠋⠙⠸⢰⣠⣄"
        # spinner = ('⣀⡀', '⣄ ', '⡆ ', '⠇ ', '⠋ ', '⠉⠁',
        #           '⠈⠉', ' ⠙', ' ⠸', ' ⢰', ' ⣠', '⢀⣀')

        for table in db.metadata.sorted_tables:
            filename = filename_template % table.name
            self.steps_so_far += 1
            fraction = float(self.steps_so_far) / float(ntables)
            pb_set_fraction(fraction)
            spinner_index = 0
            msg = _("exporting %(table)s table to %(filename)s") % {
                "table": table.name,
                "filename": filename,
            }
            msg = msg + "  " + spinner[0]
            bauble.task.set_message(msg)
            logger.info(f"exporting {table.name}")

            # Query the data
            stmt = select(table)
            # results = self.session.execute(stmt).fetchall()  # Use the session for execution
            results = self.session.execute(stmt).mappings().all()

            # create empty files with only the column names
            if len(results) == 0:
                write_csv(filename, [list(table.c.keys())])
                yield
                continue

            rows = []
            rows.append(list(table.c.keys()))  # append col names
            ctr = 0
            for row in results:
                # values = list(map(replace, list(row)))
                values = list(map(replace, [row[col] for col in table.c.keys()]))
                rows.append(values)
                if ctr == update_every:
                    spinner_index = (spinner_index + 1) % len(spinner)
                    msg = msg[: -len(spinner[0])] + spinner[spinner_index]
                    bauble.task.set_message(msg)
                    yield
                    ctr = 0
                ctr += 1
            write_csv(filename, rows)


class CSVImportCommandHandler(pluginmgr.CommandHandler):

    command: str = "imcsv"

    def __call__(self, cmd, arg) -> None:
        importer = CSVImporter()
        importer.start(arg)


class CSVExportCommandHandler(pluginmgr.CommandHandler):

    command: str = "excsv"

    def __call__(self, cmd, arg) -> None:
        exporter = CSVExporter()
        exporter.start(arg)


#
# plugin classes
#

backup_category: Any = (_("Backup"), "plugins/imex/backup.png")


class CSVImportTool(pluginmgr.Tool):
    category = backup_category
    label: Any = _("Restore")
    icon_name: str = "backup-restore.png"

    @classmethod
    def start(cls) -> None:
        """
        Start the CSV importer.  This tool will also reinitialize the
        plugins after importing.
        """
        msg = _(
            "Importing data into an existing database will "
            "replace all your existing data.\n\n"
            "<i>Would you like to continue?</i>"
        )
        if utils.yes_no_dialog(msg):
            c = CSVImporter()
            c.start()


class CSVExportTool(pluginmgr.Tool):
    category = backup_category
    label: Any = _("Create")
    icon_name: str = "backup-create.png"

    @classmethod
    def start(cls) -> None:
        c = CSVExporter()
        c.start()


# TODO: add support to import from the command line

# TODO: add support to import from the command line
# TODO: add support to import from the command line
# TODO: add support to import from the command line
# TODO: add support to import from the command line
