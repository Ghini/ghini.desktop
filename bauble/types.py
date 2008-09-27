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
    """A database independent Enum type. The value is stored in the
    database as a Unicode string.

    values:
      A list of valid values for column.
    empty_to_none:
      Treat the empty string '' as None.  None must be in the values
      list in order to set empty_to_none=True.
    """
    impl = types.Unicode

    def __init__(self, values, empty_to_none=False, strict=True, **kwargs):

        if values is None or len(values) is 0:
            raise EnumError(_('Enum requires a list of values'))
        if empty_to_none and None not in values:
            raise EnumError(_('You have configured empty_to_none=True but '\
                              'None is not in the values lists'))
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

