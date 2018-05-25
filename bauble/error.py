# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
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
# all bauble exceptions and errors
#


class BaubleError(Exception):
    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        if self.msg is None:
            return str(type(self).__name__)
        else:
            return '%s: %s' % (type(self).__name__, self.msg)
        return self.msg


class CommitException(Exception):

    def __init__(self, exc, row):
        self.row = row  # the model we were trying to commit
        self.exc = exc  # the exception thrown while committing

    def __str__(self):
        return str(self.exc)


class NoResultException(BaubleError):
    ## use this exception if the caller should return None
    pass


class DatabaseError(BaubleError):
    pass


class EmptyDatabaseError(DatabaseError):
    pass


class MetaTableError(DatabaseError):
    pass


class TimestampError(DatabaseError):
    pass


class RegistryError(DatabaseError):
    pass


class VersionError(DatabaseError):

    def __init__(self, version):
        super().__init__()
        self.version = version


class SQLAlchemyVersionError(BaubleError):
    pass


class CheckConditionError(BaubleError):
    pass


def check(condition, msg=None):
    """
    Check that condition is true.  If not then raise
    CheckConditionError(msg)
    """
    if not condition:
        raise CheckConditionError(msg)
