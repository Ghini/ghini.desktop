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
from typing import Any, cast

from pyparsing import (
    CaselessLiteral,
    Group,
    Regex,
    Word,
    WordEnd,
    WordStart,
    ZeroOrMore,
    alphanums,
    alphas,
    alphas8bit,
    delimitedList,
    oneOf,
    quotedString,
    removeQuotes,
)


class BuiltQuery:

    wordStart: Any
    wordEnd: Any
    parsed: Any
    __clauses: Any
    is_valid: bool
    wordStart, wordEnd = WordStart(), WordEnd()

    AND_: Any = wordStart + CaselessLiteral("and") + wordEnd
    OR_: Any = wordStart + CaselessLiteral("or") + wordEnd
    BETWEEN_: Any = wordStart + CaselessLiteral("between") + wordEnd

    numeric_value: Any = Regex(r"[-]?\d+(\.\d*)?([eE]\d+)?")
    unquoted_string: Any = Word(alphanums + alphas8bit + "%.-_*;:")
    string_value: Any = quotedString.setParseAction(removeQuotes) | unquoted_string
    fieldname: Any = Group(delimitedList(Word(alphas + "_", alphanums + "_"), "."))
    value: Any = numeric_value | string_value
    binop: Any = oneOf("= == != <> < <= > >= has like contains", caseless=True)
    clause: Any = fieldname + binop + value
    unparseable_clause: Any = (fieldname + BETWEEN_ + value + AND_ + value) | (
        Word(alphanums) + "(" + fieldname + ")" + binop + value
    )
    expression: Any = Group(clause) + ZeroOrMore(
        Group(
            AND_ + clause
            | OR_ + clause
            | ((OR_ | AND_) + unparseable_clause).suppress()
        )
    )
    query: Any = Word(alphas) + CaselessLiteral("where") + expression

    def __init__(self, s: str) -> None:
        self.parsed = None
        self.__clauses = None
        try:
            self.parsed = self.query.parseString(s)
            self.is_valid = True
        except:
            self.is_valid = False

    @property
    def clauses(self) -> list[Any]:
        if not self.__clauses:
            self.__clauses = [
                type(
                    "FooBar",
                    (object,),
                    dict(
                        connector=len(i) == 4 and i[0] or None,
                        field=".".join(i[-3]),
                        operator=i[-2],
                        value=i[-1],
                    ),
                )()
                for i in [k for k in self.parsed if len(k) > 0][2:]
            ]
        return cast(list[Any], self.__clauses)

    @property
    def domain(self) -> str:
        return cast(str, self.parsed[0])
