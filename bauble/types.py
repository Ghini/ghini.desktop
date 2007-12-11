#
# types.py
#

import sqlalchemy.types as types
import sqlalchemy.exceptions as exceptions
from bauble.i18n import *

class Enum(types.Unicode):

    def __init__(self, values, empty_to_none=False):
        '''
        contruct an Enum type

        values : a list of values that are valid for this column
        empty_to_none : treat the empty string '' as None
        '''
        if values is None or len(values) is 0:
            raise exceptions.AssertionError('Enum requires a list of values')
        self.empty_to_none = empty_to_none
        self.values = values
        # the length of the string/unicode column should be the longest string
        # in values
        size = max([len(v) for v in values if v is not None])
        super(Enum, self).__init__(size)


    def convert_bind_param(self, value, engine):
        if self.empty_to_none and value is '':
            value = None
        if value not in self.values:
            raise exceptions.AssertionError(_('"%s" not in Enum.values') % value)
        return super(Enum, self).convert_bind_param(value, engine)


    def convert_result_value(self, value, engine):
        if value not in self.values:
            raise exceptions.AssertionError(_('"%s" not in Enum.values') % value)
        return super(Enum, self).convert_result_value(value, engine)

