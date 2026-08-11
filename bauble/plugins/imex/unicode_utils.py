import csv
from typing import Any, Optional

import bauble.utils as utils


class UnicodeReader:

    reader: Any
    encoding: Any

    def __init__(self, f, dialect=csv.excel, encoding: str = "utf-8", **kwds) -> None:
        self.reader = csv.DictReader(f, dialect=dialect, **kwds)
        self.encoding = encoding

    def __next__(self):
        row = next(self.reader)
        t = {}
        for k, v in row.items():
            if len(v) == 0:
                t[k] = None
            else:
                t[k] = utils.to_unicode(v, self.encoding)

        return t

    def __iter__(self):
        return self


class InvalidDataError(Exception):
    pass


# TODO: add support for exporting only specific tables
class UnicodeWriter:

    writer: Any
    field_order: Any
    encoding: Any

    def __init__(
        self,
        f,
        fields: Optional[Any] = None,
        dialect=csv.excel,
        encoding: str = "utf-8",
        **kwds,
    ) -> None:
        self.writer = csv.writer(f, dialect=dialect, **kwds)
        self.field_order = fields
        self.encoding = encoding

    def writerow(self, row) -> None:
        if isinstance(row, dict):
            row = [row[k] for k in self.field_order]
        t = [utils.to_unicode(s, self.encoding) for s in row]
        self.writer.writerow(t)

    def writerows(self, rows) -> None:
        for row in rows:
            self.writerow(row)
