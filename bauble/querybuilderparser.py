#!/usr/bin/env python
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
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

# help parsing the language produced by the Query Builder, so that we can
# offer the current active query back to the Query Builder, and the
# QueryBuilder will be able to start from there
#
# if the query does not follow the grammar, start from scratch.

from pyparsing import (Word, alphas, alphanums, delimitedList, Group,
                       alphas8bit, removeQuotes, quotedString, Regex, oneOf,
                       Forward, CaselessLiteral, WordStart, WordEnd,
                       ZeroOrMore)

class BuiltQuery(object):

    wordStart, wordEnd = WordStart(), WordEnd()

    AND_ = wordStart + CaselessLiteral('and') + wordEnd
    OR_ = wordStart + CaselessLiteral('or') + wordEnd
    BETWEEN_ = wordStart + CaselessLiteral('between') + wordEnd

    numeric_value = Regex(r'[-]?\d+(\.\d*)?([eE]\d+)?')
    unquoted_string = Word(alphanums + alphas8bit + '%.-_*;:')
    string_value = (quotedString.setParseAction(removeQuotes) | unquoted_string)
    fieldname = Group(delimitedList(Word(alphas+'_', alphanums+'_'), '.'))
    value = (numeric_value | string_value)
    binop = oneOf('= == != <> < <= > >= has like contains', caseless=True)
    clause = fieldname + binop + value
    unparseable_clause = (fieldname + BETWEEN_ + value + AND_ + value) | (Word(alphanums) + '(' + fieldname + ')' + binop + value)
    expression = Group(clause) + ZeroOrMore(Group( AND_ + clause | OR_ + clause | ((OR_|AND_) + unparseable_clause).suppress()))
    query = Word(alphas) + CaselessLiteral("where") + expression

    def __init__(self, s):
        self.parsed = None
        self.__clauses = None
        try:
            self.parsed = self.query.parseString(s)
            self.is_valid = True
        except:
            self.is_valid = False
        
    @property
    def clauses(self):
        if not self.__clauses:
            self.__clauses = [type('FooBar', (object,),
                                   dict(connector=len(i)==4 and i[0] or None,
                                        field='.'.join(i[-3]),
                                        operator=i[-2],
                                        value=i[-1]))()
                              for i in [k for k in self.parsed if len(k)>0][2:]]
        return self.__clauses

    @property
    def domain(self):
        return self.parsed[0]
