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
import queue  # For producer-consumer handling

# import traceback
# from gettext import gettext as _
import threading
from collections.abc import Generator
from typing import Any, Optional

# import bauble.pluginmgr as pluginmgr
# import bauble.task
import bauble.utils as utils
import sqlalchemy as sa
from bauble.btypes import Enum
from bauble.db import Session
from bauble.plugins.imex.unicode_utils import InvalidDataError as InvalidDataError
from bauble.plugins.imex.unicode_utils import UnicodeReader as UnicodeReader
from bauble.plugins.imex.unicode_utils import UnicodeWriter as UnicodeWriter
from sqlalchemy import Boolean

# from sqlalchemy import ColumnDefault
# from sqlalchemy import inspect
# from sqlalchemy import func
# from sqlalchemy.exc import DataError
# from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.elements import ClauseElement

logger: Any = logging.getLogger(__name__)
QUOTE_STYLE: Any = csv.QUOTE_MINIMAL
QUOTE_CHAR: str = '"'
import csv as _csv

# TOP OF FILE (add)
from collections.abc import Mapping

from bauble.plugins.imex.unicode_utils import UnicodeReader

# bauble/plugins/imex/csv_processor.py
_OMIT = object()
_TEXT_TYPES = (sa.String, sa.Text, sa.Unicode, sa.CHAR, sa.VARCHAR)
_NUMERIC_TYPES = (sa.Integer, sa.BigInteger, sa.SmallInteger, sa.Numeric, sa.Float)
_TEMPORAL_TYPES = (sa.Date, sa.DateTime, sa.Time)
_BINARY_TYPES = (sa.LargeBinary, )

def preflight_csv(filename, table, max_report=50):
    """
    Scan the CSV once and report:
      - missing required (NOT NULL) columns,
      - rows where NOT NULL text columns are empty/blank,
      - enum violations (if strict),
    Returns a dict with basic stats and violation lists.
    """
    required = {c.name for c in table.c if not c.nullable}
    enums = {}
    import sqlalchemy as sa
    try:
        from bauble.btypes import Enum as BaubleEnum
    except Exception:
        BaubleEnum = None  # type: ignore

    for c in table.c:
        if isinstance(c.type, sa.Enum):
            enums[c.name] = set(getattr(c.type, "enums", []) or [])
        elif BaubleEnum and isinstance(c.type, BaubleEnum) and getattr(c.type, "strict", True):
            enums[c.name] = set(getattr(c.type, "values", []) or [])

    results = {
        "missing_headers": [],
        "empty_required_cells": [],
        "enum_violations": [],
        "row_count": 0,
    }

    with open(filename) as f:
        reader = UnicodeReader(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
        headers = set(reader.reader.fieldnames or [])
        missing = [col for col in required if col not in headers]
        results["missing_headers"] = missing

        for i, row in enumerate(reader, start=1):
            results["row_count"] = i
            # required blanks
            for col in required:
                if col in row and (row[col] is None or str(row[col]).strip() == ""):
                    col_obj = table.c[col]
                    if not getattr(col_obj, "autoincrement", False):
                        if len(results["empty_required_cells"]) < max_report:
                            results["empty_required_cells"].append((i, col))
            # enum checks
            for col, allowed in enums.items():
                if col in row and row[col] not in allowed and str(row[col]).strip() != "":
                    if len(results["enum_violations"]) < max_report:
                        results["enum_violations"].append((i, col, row[col], sorted(allowed)))

    return results

def _as_mapping(row) -> Mapping:
    """
    Return a mapping view over a row that might be:
      - SQLAlchemy Row (has ._mapping)
      - plain dict
      - sequence of (key, value) pairs
    """
    # SQLAlchemy Row / RowMapping
    mapping = getattr(row, "_mapping", None)
    if mapping is not None:
        return mapping
    # Already a dict / mapping
    if isinstance(row, Mapping):
        return row
    # Last resort: try to coerce to dict
    try:
        return dict(row)
    except Exception:
        raise TypeError(f"Cannot treat object as mapping: {type(row)!r}")


class CSVProcessor:
    table: Any
    filename: Any
    defaults: Any
    update_every: Any
    column_keys: Any
    insert_stmt: Any
    values: Any
    flush_count: Any
    steps_so_far: Any
    batch_queue: Any
    worker_thread: Any
    use_thread: bool
    worker_error: Optional[Exception]


    def __init__(
        self,
        table,
        filename,
        defaults,
        update_every,
        flush_count: int = 0,
        steps_so_far: int = 0,
        use_thread: bool = False,   # 🔴 default to synchronous for now
    ) -> None:
        """
        Initialize the CSV processor.

        :param table: SQLAlchemy Table object to insert data into.
        :param filename: Path to the CSV file.
        :param session: SQLAlchemy session object.
        :param defaults: Precomputed default values for the table.
        :param update_every: Number of rows to process before yielding and committing.
        :param use_thread: If True, insert on a background thread.
        """
        self.table = table
        self.filename = filename
        self.defaults = defaults
        self.update_every = update_every
        self.column_keys = None  # Determined after file analysis
        self.insert_stmt = self.table.insert()
        self.values = []  # Batch of rows to insert
        self.flush_count = flush_count
        self.steps_so_far = steps_so_far

        self.use_thread = use_thread
        self.worker_error = None

        if self.use_thread:
            import queue
            import threading

            # 🆕 **Thread-safe Queue for batch inserts**
            self.batch_queue = queue.Queue()

            # 🆕 **Start a worker thread to process inserts in order**
            self.worker_thread = threading.Thread(target=self._batch_worker, daemon=True)
            self.worker_thread.start()
        else:
            self.batch_queue = None
            self.worker_thread = None
            
    # @staticmethod
    # def _toposort_file(filename, key_pairs):
    #     """
    #     filename: the csv file to sort

    #     key_pairs: tuples of the form (parent, child) where for each
    #     line in the file the line[parent] needs to be sorted before
    #     any of the line[child].  parent is usually the name of the
    #     foreign_key column and child is usually the column that the
    #     foreign key points to, e.g ('parent_id', 'id')
    #     """
    #     print(f"Performing topological sorting for {filename} using key pairs: {key_pairs}")
    #     f = open(filename)
    #     reader = UnicodeReader(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)

    #     # create a dictionary of the lines mapped to the child field
    #     bychild = {}
    #     for line in reader:
    #         for parent, child in key_pairs:
    #             bychild[line[child]] = line
    #     print(f"Initial unsorted rows: {list(bychild.values())[:5]}")  # Print first few rows
    #     f.close()
    #     fields = reader.reader.fieldnames
    #     del reader

    #     # create pairs from the values in the lines where pair[0]
    #     # should come before pair[1] when the lines are sorted
    #     pairs = []
    #     for line in list(bychild.values()):
    #         for parent, child in key_pairs:
    #             if line[parent] and line[child]:
    #                 pairs.append((line[parent], line[child]))

    #     # sort the keys and flatten the lines back into a list
    #     sorted_keys = utils.topological_sort(list(bychild.keys()), pairs)
    #     print(f"Sorted order of keys: {sorted_keys[:10]}")  # Print first 10 sorted keys
    #     sorted_lines = []
    #     for key in sorted_keys:
    #         sorted_lines.append(bychild[key])
    #     # Check if sorting actually made a difference
    #     if list(bychild.keys()) != sorted_keys:
    #         print("Topological sort altered row order!")

    #     # write a temporary file of the sorted lines
    #     import tempfile

    #     tmppath = tempfile.mkdtemp()
    #     head, tail = os.path.split(filename)
    #     filename = os.path.join(tmppath, tail)
    #     tmpfile = open(filename, "w")
    #     tmpfile.write("%s\n" % ",".join(fields))
    #     writer = UnicodeWriter(
    #         tmpfile, fields=fields, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE
    #     )
    #     writer.writerows(sorted_lines)
    #     tmpfile.flush()
    #     tmpfile.close()
    #     del writer
    #     return filename
    @staticmethod
    def _toposort_file(filename, key_pairs):
        """
        Perform a topological sort of a CSV file based on foreign key dependencies.

        :param filename: The CSV file to sort
        :param key_pairs: tuples of the form (parent, child) where for each
        line in the file the line[parent] needs to be sorted before
        any of the line[child].  parent is usually the name of the
        foreign_key column and child is usually the column that the
        foreign key points to, e.g ('parent_id', 'id')
        :return: Path to the sorted CSV file
        """
        print(
            f"🔍 Performing topological sorting for {filename} using key pairs: {key_pairs}"
        )

        with open(filename) as f:
            reader = UnicodeReader(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
            fields = reader.reader.fieldnames  # Extract header fields

            # Store all rows indexed by their ID
            all_nodes = {}
            root_nodes = []
            dependency_graph = {}

            rows = []
            for line in reader:
                rows.append(line)
                child_key = line.get("id")
                parent_key = line.get("parent_id")

                # Convert to integer if possible
                if child_key.isdigit():
                    child_key = int(child_key)
                if parent_key and parent_key.isdigit():
                    parent_key = int(parent_key)
                else:
                    parent_key = None

                # Store in dictionary
                all_nodes[child_key] = line

                if parent_key is None:
                    root_nodes.append(line)  # Root-level nodes
                else:
                    # Track parent-child dependencies
                    dependency_graph.setdefault(parent_key, []).append(child_key)

        # 🔎 Debug: Check all root nodes
        print(
            f"✅ Found {len(root_nodes)} root nodes (should include continents like Europe, Africa, etc.)"
        )
        root_ids = [node["id"] for node in root_nodes]
        print(f"🟢 Root node IDs: {root_ids}")

        # Ensure all parents exist
        missing_parents = set(dependency_graph.keys()) - set(all_nodes.keys())
        if missing_parents:
            print(
                f"❌ ERROR: The following parent IDs are missing from the dataset: {missing_parents}"
            )
            exit(1)  # Stop execution

        # Create dependency pairs
        pairs = []
        for parent_key, children in dependency_graph.items():
            for child_key in children:
                if parent_key in all_nodes and child_key in all_nodes:
                    pairs.append((parent_key, child_key))

        print(f"🔗 Dependency pairs (first 20): {pairs[:20]}")

        # Perform topological sorting
        sorted_keys = utils.topological_sort(list(all_nodes.keys()), pairs)

        # 🔥 Ensure root nodes come first
        sorted_keys = [int(k) for k in sorted_keys]  # Ensure sorting by int
        sorted_keys = sorted(root_ids) + [k for k in sorted_keys if k not in root_ids]

        print(f"✅ Final sorted order of keys (first 10): {sorted_keys[:10]}")

        # Build sorted file
        sorted_lines = [all_nodes[k] for k in sorted_keys if k in all_nodes]

        # Write sorted data to temp file
        import tempfile

        tmppath = tempfile.mkdtemp()
        head, tail = os.path.split(filename)
        sorted_filename = os.path.join(tmppath, tail)

        with open(sorted_filename, "w") as tmpfile:
            tmpfile.write("{}\n".format(",".join(fields)))  # Write header
            writer = UnicodeWriter(
                tmpfile, fields=fields, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE
            )
            writer.writerows(sorted_lines)

        print(f"✅ Sorted file saved as: {sorted_filename}")
        return sorted_filename

    def prepare_file(self) -> None:
        """
        Prepare the file by determining column keys and sorting rows if necessary.
        """
        csv_columns = self._extract_csv_columns()
        if self._has_self_referencing_keys():
            self.filename = self._sort_by_foreign_keys()

        # Keep only columns that actually exist on the table; append defaults that are real cols.
        table_cols = set(self.table.c.keys())
        ordered = [c for c in csv_columns if c in table_cols]
        default_only = [c for c in self.defaults.keys() if c in table_cols and c not in ordered]
        self.column_keys = ordered + default_only

        # Core insert for the table
        self.insert_stmt = self.table.insert()

    def process_rows(self) -> Generator[Any, None, None]:
        """
        Process the CSV rows, applying defaults and preparing for batch insertion.
        Yields control after every `update_every` rows for GUI updates.
        """
        steps_so_far = 0
        batch_queue = []  # Store rows for batch insert

        with open(self.filename) as f:
            reader = UnicodeReader(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
            for row in reader:
                cleaned_row = self._process_row(row)
                batch_queue.append(cleaned_row)
                steps_so_far += 1

                if steps_so_far % self.update_every == 0:
                    self._insert_batch(batch_queue)  # Insert current batch
                    batch_queue.clear()  # Clear queue before yielding
                    logger.debug(
                        f"✅ Batch inserted. Yielding at step {steps_so_far}..."
                    )

                    yield steps_so_far
                    logger.debug("Resumed after yield.")

        # Insert remaining rows
        if batch_queue:
            self._insert_batch(batch_queue)

        yield steps_so_far

    def _extract_csv_columns(self):
        """
        Return the set of CSV column names without consuming any data row.
        (We only need DictReader.fieldnames; don't advance the iterator.)
        """
        with open(self.filename) as f:
            reader = UnicodeReader(f, quotechar=QUOTE_CHAR, quoting=QUOTE_STYLE)
            #next(reader)  # Skip the header
            #return set(reader.reader.fieldnames)
            dict_reader = getattr(reader, "reader", reader)
            fieldnames = getattr(dict_reader, "fieldnames", None)
            if not fieldnames:
                raise ValueError(
                    "CSV reader does not expose 'fieldnames'; expected a DictReader-like object."
                )
            # keep behavior compatible with existing code that expects a set,
            # but do not mutate/advance the reader.
            return [fn.strip() if isinstance(fn, str) else fn for fn in fieldnames]
        
    def _has_self_referencing_keys(self):
        return any(fk.column.table == self.table for fk in self.table.foreign_keys)

    def _sort_by_foreign_keys(self):
        key_pairs = [
            (fk.parent.name, fk.column.name)
            for fk in self.table.foreign_keys
            if fk.column.table == self.table
        ]
        print(f"Sorting {self.filename} based on foreign key dependencies: {key_pairs}")

        sorted_filename = self._toposort_file(self.filename, key_pairs)

        print(f"Sorted file saved as: {sorted_filename}")

        return sorted_filename

    def cleanup(self) -> None:
        """
        Ensure all batches are processed before exiting.

        In synchronous mode (use_thread=False) there's nothing to do.
        In threaded mode, wait for the queue to drain, stop the worker,
        and surface any worker error.
        """
        if not self.use_thread:
            return

        # Wait for all queued batches to be processed
        if self.batch_queue is not None:
            try:
                self.batch_queue.join()
                # Tell the worker to exit and wait for it
                self.batch_queue.put(None)
            except Exception:
                logger.exception("Failed while draining batch queue in cleanup()")

        if self.worker_thread is not None:
            try:
                self.worker_thread.join()
            except Exception:
                logger.exception("Failed to join worker thread in cleanup()")

        # # If the worker failed, raise so the caller can show the error
        # if self.worker_error is not None:
        #     raise RuntimeError(
        #         f"Background insert failed for table {self.table.name}"
        #     ) from self.worker_error
        #return

    def _process_row(self, row):
        """
        Normalize and apply defaults to a single row from the CSV file.
        """
        cleaned_row = {}
        for column in self.column_keys:
            value = row.get(column, self.defaults.get(column))
            norm = self._normalize_value(value, column)
            if norm is _OMIT:
                # don't include this column at all (let SA/server defaults handle it)
                continue
            cleaned_row[column] = norm
        return cleaned_row

    def _normalize_value(self, value, column):
        """
        Normalize the value for a given column, handling types and defaults.
        """
        # Skip SQLAlchemy objects (e.g., expressions like `func.now()`)
        if isinstance(value, ClauseElement):
            return value  # Return as-is for SQL expressions like `now()`

        col = self.table.c[column]
        column_type = col.type
        is_empty = (value is None) or (isinstance(value, str) and value.strip() in ("", "None"))

        if is_empty:
            if hasattr(self, "Defaults")and column in self.defaults:
                return self.defaults[column]
            autoinc = getattr(col, "autoincrement", None)
            if col.primary_key or autoinc not in (False, None) or isinstance(column_type, _NUMERIC_TYPES + _TEMPORAL_TYPES + (Boolean,) + _BINARY_TYPES):
                return _OMIT
 
            if isinstance(column_type, Enum) and getattr(column_type, "empty_to_none", False):
                return None
            
            if not col.nullable:
                if isinstance(column_type, _TEXT_TYPES):
                    return ""
                raise InvalidDataError(f"Column '{column}' is NOT NULL but CSV provides empty/blank.")
            return None



#            if (not col.nullable) and isinstance(column_type, _TEXT_TYPES):
#                return ""
#            return _OMIT

        try:

            if isinstance(column_type, Boolean):
                if isinstance(value, str):
                    v = value.lower()
                    if v in ("true", "t", "1", "yes", "y"):
                        return True
                    if v in ("false", "f", "0", "no", "n"):
                        return False
                return bool(value)                    

            elif isinstance(column_type, sa.Integer):
                return int(value)

            elif isinstance(column_type, sa.Float):
                return float(value)

            elif isinstance(column_type, sa.Enum):  # SQLAlchemy Enum
                allowed = list(getattr(column_type, "enums", []) or [])
                if value not in allowed:
                    raise InvalidDataError(
                        f"Invalid value for column '{column}': {value}. "
                        f"Allowed values are: {allowed}"
                    )
                return value  # Keep as string for DB insertion

            elif isinstance(column_type, Enum):  # Custom Enum
                allowed = list(getattr(column_type, "values", []) or [])
                strict = getattr(column_type, "strict", True)
                if strict and value not in allowed:
                    raise InvalidDataError(
                        f"Invalid value for column '{column}': {value}. "
                        f"Expected one of: {allowed}"
                    )
                return value

        except ValueError:
            raise InvalidDataError(f"Invalid value for column '{column}': {value}")

        return value  # Return as-is for any other data types
    
    def _execute_batch_now(self, values: list[dict]) -> None:
        """Synchronous insert path (same thread).  Minimal hardening + proper executemany."""
        if not values:
            return

        # ---- minimal preflight: ensure list[dict]-like ----
        if isinstance(values, tuple):
            values = list(values)

        fixed = []
        for i, row in enumerate(values):
            if isinstance(row, dict):
                fixed.append(row)
                continue
            # allow (key, value) iterable; otherwise fail with a clear message
            try:
                as_dict = dict(row)
            except Exception as exc:
                raise TypeError(
                    f"_execute_batch_now expected dicts; row {i} is {type(row).__name__} "
                    f"and cannot be coerced to dict."
                ) from exc
            fixed.append(as_dict)

        # ★ Ensure every row has the same set of keys (pad missing with None)
        table_cols = set(self.table.c.keys())
        all_keys = set().union(*(r.keys() for r in fixed)) & table_cols
        for r in fixed:
            for k in all_keys:
                r.setdefault(k, None)
                
        # ---- executemany: statement + list-of-dicts (no .values(...)) ----
        from sqlalchemy.exc import SQLAlchemyError
        with Session() as s:
            try:
                s.execute(self.insert_stmt, fixed)
                if s.in_transaction():
                    s.commit()
                self.flush_count += 1
                logger.debug("Flushed batch #%s for %s (sync)", self.flush_count, self.table.name)
            except SQLAlchemyError as e:
                logger.exception("Batch insert failed for %s", self.table.name)
                if s.in_transaction():
                    s.rollback()
                if self.worker_error is None:
                    self.worker_error = e
                raise


    def _batch_worker(self) -> None:
        while True:
            batch = self.batch_queue.get()
            if batch is None:
                self.batch_queue.task_done()
                break  # Exit signal received
            try:
                self._execute_batch_now(batch)
            except Exception as e:
                # remember the first error and keep draining so .join() returns
                if self.worker_error is None:
                    self.worker_error = e
                logger.exception("Error inserting batch in %s", self.table.name)
            finally:
                self.batch_queue.task_done()



    from typing import Any, Iterable, Mapping, Optional

    def _insert_batch(
        self, batch_values: Optional[Iterable[Mapping[str, Any]]] = None
    ) -> None:
        """
        Queue (or execute) a batch of rows. Accepts dicts or Row objects.
        Ensures we pass list[dict] with only valid table columns to SQLAlchemy.
        """
        table_cols = set(self.table.c.keys())

        def convert_enum(value: Any) -> Any:
            # Use the Enum from this codebase (not sqlalchemy.Enum)
            from bauble.btypes import Enum as BaubleEnum
            return value.value if isinstance(value, BaubleEnum) else value

        values_to_insert = batch_values if batch_values is not None else self.values
        if not values_to_insert:
            return

        fixed_values: list[dict] = []
        for row in values_to_insert:
            # Support Row/RowMapping, dict, or any mapping-like
            mapping = getattr(row, "_mapping", row)
            if not isinstance(mapping, Mapping):
                # Last resort: try to coerce (list of pairs, etc.)
                try:
                    mapping = dict(mapping)
                except Exception as exc:
                    raise TypeError(
                        f"Insert row for {self.table.name} is not a mapping and cannot be coerced: {type(row)!r}"
                    ) from exc

            # Keep only valid table columns; convert enums
            coerced = {}
            for k, v in mapping.items():
                if k not in table_cols:
                    continue
                if v is _OMIT:
                    continue
                coerced[k] = convert_enum(v)
            fixed_values.append(coerced)

        # Execute now or hand to the worker
        if self.use_thread:
            self.batch_queue.put(fixed_values)
        else:
            self._execute_batch_now(fixed_values)

        if batch_values is None:
            self.values.clear()

            self.values.clear()

