#
# types.py
#

import sqlalchemy.types as types
import sqlalchemy.exc as exc
from bauble.i18n import *
import bauble.error as error


class EnumError(error.BaubleError):
    """Raised when a bad value is inserted or returned from the Enum type"""


class Enum(types.TypeDecorator):
    """Emulate an Enum type.

    valus:
      A list of value values for this column
    empty
    values : a list of values that are valid for this column
    empty_to_none : treat the empty string '' as None
    """

    impl = types.Unicode

    def __init__(self, values, empty_to_none=False, strict=True, **kwargs):

        if values is None or len(values) is 0:
            raise EnumError('Enum requires a list of values')
        self.values = values[:]
        self.strict = strict
        self.empty_to_none = empty_to_none
        # the length of the string/unicode column should be the
        # longest string in values
        size = max([len(v) for v in values if v is not None])
        super(Enum, self).__init__(size, **kwargs)


    def process_bind_param(self, value, dialect):
        """
        Process the value going into the database.
        """
        if self.empty_to_none and value is '':
            value = None
        if value not in self.values:
            raise EnumError(_('"%s" not in Enum.values: %s') % \
                             (value, self.values))
        return value


    def process_result_value(self, value, dialect):
        """
        Process the value returned from the database.
        """
        if self.strict and value not in self.values:
            raise ValueError(_('"%s" not in Enum.values') % value)
        return value


    def copy(self):
        return Enum(self.values, self.empty_to_none, self.strict)



def test_enum():
    """
    """
    e = Enum(['1', '2'])
    e.process_bind_param('1', None)

