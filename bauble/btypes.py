# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2017 Mario Frasca <mario@anche.no>
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
# types.py
#

import sqlalchemy.types as types
import logging
logger = logging.getLogger(__name__)


import bauble.error as error

# TODO: store all times as UTC or support timezones


class EnumError(error.BaubleError):
    """Raised when a bad value is inserted or returned from the Enum type"""


class Enum(types.TypeDecorator):
    """A database independent Enum type. The value is stored in the
    database as a Unicode string.
    """
    impl = types.Unicode

    def __init__(self, values, empty_to_none=False, strict=True,
                 translations={}, **kwargs):
        """
        : param values: A list of valid values for column.
        :param empty_to_none: Treat the empty string '' as None.  None
        must be in the values list in order to set empty_to_none=True.
        :param strict:
        :param translations: A dictionary of values->translation
        """
        # create the translations from the values and set those from
        # the translations argument, this way if some translations are
        # missing then the translation will be the same as value
        logger.debug('Enum::init %s %s %s' % (type(self).__name__, values, empty_to_none))
        if values is None or len(values) == 0:
            raise EnumError(_('Enum requires a list of values'))
        if not set(type(x) for x in values).issubset({type(None), str}):
            raise EnumError(_('Enum requires string values (or None)'))
        if len(values) != len(set(values)):
            raise EnumError(_('Enum requires the values to be different'))
        self.translations = dict((v, v) for v in values)
        for key, value in translations.items():
            self.translations[key] = value
        if empty_to_none and (None not in values):
            raise EnumError(_('You have configured empty_to_none=True but '
                              'None is not in the values lists'))
        self.values = values[:]
        self.strict = strict
        self.empty_to_none = empty_to_none
        # the length of the string/unicode column should be the
        # longest string in values
        size = max([len(v) for v in values if v is not None])
        super().__init__(size, **kwargs)

    def process_bind_param(self, value, dialect):
        """
        Process the value going into the database.
        """
        logger.debug('Enum::process_bind_param %s %s(%s)' % (type(self).__name__, type(value).__name__, value))
        if (self.empty_to_none) and (not value):
            value = None
        if value not in self.values:
            raise EnumError(_('%(type_name)s(%(value)s) not in Enum.values: %(all_values)s'
                              ) % {'value': value,
                                   'type_name': type(value).__name__,
                                   'all_values': self.values})
        return value

    def process_result_value(self, value, dialect):
        """
        Process the value returned from the database.
        """
        # if self.strict and value not in self.values:
        #     raise ValueError(_('"%s" not in Enum.values') % value)
        return value

    def copy(self):
        return Enum(self.values, self.empty_to_none, self.strict)


from bauble.utils import parse_date

class DateTime(types.TypeDecorator):
    """
    A DateTime type that allows strings
    """
    impl = types.DateTime

    import re
    _rx_tz = re.compile('[+-]')

    def process_bind_param(self, value, dialect):
        if not isinstance(value, str):
            return value
        try:
            DateTime._dayfirst
            DateTime._yearfirst
        except AttributeError:
            import bauble.prefs as prefs
            DateTime._dayfirst = prefs.prefs[prefs.parse_dayfirst_pref]
            DateTime._yearfirst = prefs.prefs[prefs.parse_yearfirst_pref]
        result = parse_date(
            value, dayfirst=DateTime._dayfirst, yearfirst=DateTime._yearfirst)
        return result

    def process_result_value(self, value, dialect):
        return value

    def copy(self):
        return DateTime()


class Date(types.TypeDecorator):
    """
    A Date type that allows Date strings
    """
    impl = types.Date

    def process_bind_param(self, value, dialect):
        if not isinstance(value, str):
            return value
        try:
            Date._dayfirst
            Date._yearfirst
        except AttributeError:
            import bauble.prefs as prefs
            Date._dayfirst = prefs.prefs[prefs.parse_dayfirst_pref]
            Date._yearfirst = prefs.prefs[prefs.parse_yearfirst_pref]
        return parse_date(
            value, dayfirst=Date._dayfirst, yearfirst=Date._yearfirst).date()

    def process_result_value(self, value, dialect):
        return value

    def copy(self):
        return Date()

