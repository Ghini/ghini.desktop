# -*- coding: utf-8 -*-
#
# Copyright 2008, 2009, 2010 Brett Adams
# Copyright 2014-2015 Mario Frasca <mario@anche.no>.
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


import weakref

from gi.repository import Gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from sqlalchemy import or_, and_
from sqlalchemy import Unicode
from sqlalchemy import UnicodeText
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm.properties import (
    ColumnProperty, RelationshipProperty)
RelationProperty = RelationshipProperty

import bauble
from bauble.error import check
import bauble.utils as utils

from bauble.editor import (
    GenericEditorView, GenericEditorPresenter)


def search(text, session=None):
    results = set()
    for strategy in list(_search_strategies.values()):
        logger.debug("applying search strategy %s from module %s" %
                     (type(strategy).__name__, type(strategy).__module__))
        results.update(strategy.search(text, session))
    return list(results)


class NoneToken(object):
    def __init__(self, t=None):
        pass

    def __repr__(self):
        return '(None<NoneType>)'

    def express(self):
        return None


class EmptyToken(object):
    def __init__(self, t=None):
        pass

    def __repr__(self):
        return 'Empty'

    def express(self):
        return set()

    def __eq__(self, other):
        if isinstance(other, EmptyToken):
            return True
        if isinstance(other, set):
            return len(other) == 0
        return NotImplemented


class ValueABC(object):
    ## abstract base class.

    def express(self):
        return self.value


class ValueToken(object):

    def __init__(self, t):
        self.value = t[0]

    def __repr__(self):
        return repr(self.value)

    def express(self):
        return self.value.express()


class StringToken(ValueABC):
    def __init__(self, t):
        self.value = t[0]  # no need to parse the string

    def __repr__(self):
        return "'%s'" % (self.value)


class NumericToken(ValueABC):
    def __init__(self, t):
        self.value = float(t[0])  # store the float value

    def __repr__(self):
        return "%s" % (self.value)

def smartdatetime(year_or_offset, *args):
    """return either datetime.datetime, or a day with given offset.

    When given only one argument, this is interpreted as an offset for
    timedelta, and it is added to datetime.today().  If given more
    arguments, it just behaves as datetime.datetime.

    """
    from datetime import datetime, timedelta
    if not args:
        return (datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(year_or_offset))
    else:
        return datetime(year_or_offset, *args)

def smartboolean(*args):
    """translate args into boolean value

    Result is True whenever first argument is not numerically zero nor
    literally 'false'.  No arguments cause error.

    """
    if len(args) == 1:
        try:
            return float(args[0]) != 0.0
        except:
            return args[0].lower() != 'false'
    return True


class TypedValueToken(ValueABC):
    ## |<name>|<paramlist>|
    constructor = {'datetime': (smartdatetime, int),
                   'bool': (smartboolean, str),
                   }

    def __init__(self, t):
        logger.debug('constructing typedvaluetoken %s' % str(t))
        try:
            constructor, converter = self.constructor[t[1]]
        except KeyError:
            return
        params = tuple(converter(i) for i in t[3].express())
        self.value = constructor(*params)

    def __repr__(self):
        return "%s" % (self.value)


class IdentifierAction(object):
    def __init__(self, t):
        logger.debug('IdentifierAction::__init__(%s)' % t)
        self.steps = t[0][:-2:2]
        self.leaf = t[0][-1]

    def __repr__(self):
        return '.'.join(self.steps + [self.leaf])

    def evaluate(self, env):
        """return pair (query, attribute)

        the value associated to the identifier is an altered query where the
        joinpoint is the one relative to the attribute, and the attribute
        itself.
        """
        query = env.session.query(env.domain)
        if len(self.steps) == 0:
            # identifier is an attribute of the table being queried
            cls = env.domain
        else:
            # identifier is an attribute of a joined table
            query = query.join(*self.steps, aliased=True)
            cls = query._joinpoint['_joinpoint_entity']
        attr = getattr(cls, self.leaf)
        logger.debug('IdentifierToken for %s, %s evaluates to %s'
                     % (cls, self.leaf, attr))
        return (query, attr)

    def needs_join(self, env):
        return self.steps


class FilteredIdentifierAction(object):
    def __init__(self, t):
        logger.debug('FilteredIdentifierAction::__init__(%s)' % t)
        self.steps = t[0][:-7:2]
        self.filter_attr = t[0][-6]
        self.filter_op = t[0][-5]
        self.filter_value = t[0][-4]
        self.leaf = t[0][-1]

        # cfr: SearchParser.binop
        # = == != <> < <= > >= not like contains has ilike icontains ihas is
        self.operation = {
            '=': lambda x, y: x == y,
            '==': lambda x, y: x == y,
            'is': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '<>': lambda x, y: x != y,
            'not': lambda x, y: x != y,
            '<': lambda x, y: x < y,
            '<=': lambda x, y: x <= y,
            '>': lambda x, y: x > y,
            '>=': lambda x, y: x >= y,
            'like': lambda x, y: utils.ilike(x, '%s' % y),
            'contains': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            'has': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            'ilike': lambda x, y: utils.ilike(x, '%s' % y),
            'icontains': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            'ihas': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            }.get(self.filter_op)

    def __repr__(self):
        return "%s[%s%s%s].%s" % ('.'.join(self.steps),
                                  self.filter_attr, self.filter_op, self.filter_value,
                                  self.leaf)

    def evaluate(self, env):
        """return pair (query, attribute)"""
        query = env.session.query(env.domain)
        # identifier is an attribute of a joined table
        query = query.join(*self.steps, aliased=True)
        cls = query._joinpoint['_joinpoint_entity']
        attr = getattr(cls, self.filter_attr)
        clause = lambda x: self.operation(attr, x)
        logger.debug('filtering on %s(%s)' % (type(attr), attr))
        query = query.filter(clause(self.filter_value.express()))
        attr = getattr(cls, self.leaf)
        logger.debug('IdentifierToken for %s, %s evaluates to %s'
                     % (cls, self.leaf, attr))
        return (query, attr)

    def needs_join(self, env):
        return self.steps


class IdentExpression(object):
    def __init__(self, t):
        logger.debug('IdentExpression::__init__(%s)' % t)
        self.op = t[0][1]

        # cfr: SearchParser.binop
        # = == != <> < <= > >= not like contains has ilike icontains ihas is
        self.operation = {
            '=': lambda x, y: x == y,
            '==': lambda x, y: x == y,
            'is': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '<>': lambda x, y: x != y,
            'not': lambda x, y: x != y,
            '<': lambda x, y: x < y,
            '<=': lambda x, y: x <= y,
            '>': lambda x, y: x > y,
            '>=': lambda x, y: x >= y,
            'like': lambda x, y: utils.ilike(x, '%s' % y),
            'contains': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            'has': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            'ilike': lambda x, y: utils.ilike(x, '%s' % y),
            'icontains': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            'ihas': lambda x, y: utils.ilike(x, '%%%s%%' % y),
            }.get(self.op)
        self.operands = t[0][0::2]  # every second object is an operand

    def __repr__(self):
        return "(%s %s %s)" % (self.operands[0], self.op, self.operands[1])

    def evaluate(self, env):
        q, a = self.operands[0].evaluate(env)
        if self.operands[1].express() == set():
            # check against the empty set
            if self.op in ('is', '=', '=='):
                return q.filter(~a.any())
            elif self.op in ('not', '<>', '!='):
                return q.filter(a.any())
        clause = lambda x: self.operation(a, x)
        logger.debug('filtering on %s(%s)' % (type(a), a))
        return q.filter(clause(self.operands[1].express()))

    def needs_join(self, env):
        return [self.operands[0].needs_join(env)]


class ElementSetExpression(IdentExpression):
    # currently only implements `in`

    def evaluate(self, env):
        q, a = self.operands[0].evaluate(env)
        return q.filter(a.in_(self.operands[1].express()))


class AggregatedExpression(IdentExpression):
    '''select on value of aggregated function

    this one looks like ident.binop.value, but the ident is an
    aggregating function, so that the query has to be altered
    differently: not filter, but group_by and having.
    '''

    def __init__(self, t):
        super().__init__(t)
        logger.debug('AggregatedExpression::__init__(%s)' % t)

    def evaluate(self, env):
        # operands[0] is the function/identifier pair
        # operands[1] is the value against which to test
        # operation implements the clause
        q, a = self.operands[0].identifier.evaluate(env)
        from sqlalchemy.sql import func
        f = getattr(func, self.operands[0].function)
        clause = lambda x: self.operation(f(a), x)
        # group by main ID
        # apply having
        main_table = q.column_descriptions[0]['type']
        mta = getattr(main_table, 'id')
        logger.debug('filtering on %s(%s)' % (type(mta), mta))
        result = q.group_by(mta).having(clause(self.operands[1].express()))
        return result


class BetweenExpressionAction(object):
    def __init__(self, t):
        self.operands = t[0][0::2]  # every second object is an operand

    def __repr__(self):
        return "(BETWEEN %s %s %s)" % tuple(self.operands)

    def evaluate(self, env):
        q, a = self.operands[0].evaluate(env)
        clause_low = lambda low: low <= a
        clause_high = lambda high: a <= high
        return q.filter(and_(clause_low(self.operands[1].express()),
                             clause_high(self.operands[2].express())))

    def needs_join(self, env):
        return [self.operands[0].needs_join(env)]


class UnaryLogical(object):
    ## abstract base class. `name` is defined in derived classes
    def __init__(self, t):
        self.op, self.operand = t[0]

    def __repr__(self):
        return "%s %s" % (self.name, str(self.operand))

    def needs_join(self, env):
        return self.operand.needs_join(env)


class BinaryLogical(object):
    ## abstract base class. `name` is defined in derived classes
    def __init__(self, t):
        self.op = t[0][1]
        self.operands = t[0][0::2]  # every second object is an operand

    def __repr__(self):
        return "(%s %s %s)" % (self.operands[0], self.name, self.operands[1])

    def needs_join(self, env):
        return self.operands[0].needs_join(env) + \
            self.operands[1].needs_join(env)


class SearchAndAction(BinaryLogical):
    name = 'AND'

    def evaluate(self, env):
        result = self.operands[0].evaluate(env)
        for i in self.operands[1:]:
            result = result.intersect(i.evaluate(env))
        return result


class SearchOrAction(BinaryLogical):
    name = 'OR'

    def evaluate(self, env):
        result = self.operands[0].evaluate(env)
        for i in self.operands[1:]:
            result = result.union(i.evaluate(env))
        return result


class SearchNotAction(UnaryLogical):
    name = 'NOT'

    def evaluate(self, env):
        q = env.session.query(env.domain)
        for i in env.domains:
            q.join(*i)
        return q.except_(self.operand.evaluate(env))


class ParenthesisedQuery(object):
    def __init__(self, t):
        self.content = t[1]

    def __repr__(self):
        return "(%s)" % self.content.__repr__()

    def evaluate(self, env):
        return self.content.evaluate(env)

    def needs_join(self, env):
        return self.content.needs_join(env)


class QueryAction(object):
    def __init__(self, t):
        self.domain = t[0]
        self.filter = t[1][0]

    def __repr__(self):
        return "SELECT * FROM %s WHERE %s" % (self.domain, self.filter)

    def invoke(self, search_strategy):
        """
        update search_strategy object with statement results

        Queries can use more database specific features.  This also
        means that the same query might not work the same on different
        database types. For example, on a PostgreSQL database you can
        use ilike but this would raise an error on SQLite.
        """

        logger.debug('QueryAction:invoke - %s(%s) %s(%s)' %
                     (type(self.domain), self.domain,
                      type(self.filter), self.filter))
        domain = self.domain
        check(domain in search_strategy._domains or
              domain in search_strategy._shorthand,
              'Unknown search domain: %s' % domain)
        self.domain = search_strategy._shorthand.get(domain, domain)
        self.domain = search_strategy._domains[domain][0]
        self.search_strategy = search_strategy

        result = set()
        if search_strategy._session is not None:
            self.domains = self.filter.needs_join(self)
            self.session = search_strategy._session
            records = self.filter.evaluate(self).all()
            result.update(records)

        if None in result:
            logger.warn('removing None from result set')
            result = set(i for i in result if i is not None)
        return result


class StatementAction(object):
    def __init__(self, t):
        self.content = t[0]
        self.invoke = lambda x: self.content.invoke(x)

    def __repr__(self):
        return repr(self.content)


class BinomialNameAction(object):
    """created when the parser hits a binomial_name token.

    Searching using binomial names returns one or more species objects.
    """

    def __init__(self, t):
        self.genus_epithet = t[0]
        self.species_epithet = t[1]

    def __repr__(self):
        return "%s %s" % (self.genus_epithet, self.species_epithet)

    def invoke(self, search_strategy):
        logger.debug('BinomialNameAction:invoke')
        from bauble.plugins.plants.genus import Genus
        from bauble.plugins.plants.species import Species
        result = search_strategy._session.query(Species).filter(
            or_(Species.sp.startswith(self.species_epithet),
                and_(self.species_epithet == 'sp', Species.infrasp1 == 'sp'))).join(Genus).filter(
            Genus.genus.startswith(self.genus_epithet)).all()
        result = set(result)
        if None in result:
            logger.warn('removing None from result set')
            result = set(i for i in result if i is not None)
        return result


class DomainExpressionAction(object):
    """created when the parser hits a domain_expression token.

    Searching using domain expressions is a little more magical than an
    explicit query. you give a domain, a binary_operator and a value,
    the domain expression will return all object with at least one
    property (as passed to add_meta) matching (according to the binop)
    the value.
    """

    def __init__(self, t):
        self.domain = t[0]
        self.cond = t[1]
        self.values = t[2]

    def __repr__(self):
        return "%s %s %s" % (self.domain, self.cond, self.values)

    def invoke(self, search_strategy):
        logger.debug('DomainExpressionAction:invoke')
        try:
            if self.domain in search_strategy._shorthand:
                self.domain = search_strategy._shorthand[self.domain]
            cls, properties = search_strategy._domains[self.domain]
        except KeyError:
            raise KeyError(_('Unknown search domain: %s') % self.domain)

        query = search_strategy._session.query(cls)

        ## here is the place where to optionally filter out unrepresented
        ## domain values. each domain class should define its own 'I have
        ## accessions' filter. see issue #42

        result = set()

        # select all objects from the domain
        if self.values == '*':
            result.update(query.all())
            return result

        mapper = class_mapper(cls)

        if self.cond in ('like', 'ilike'):
            condition = lambda col: \
                lambda val: utils.ilike(mapper.c[col], '%s' % val)
        elif self.cond in ('contains', 'icontains', 'has', 'ihas'):
            condition = lambda col: \
                lambda val: utils.ilike(mapper.c[col], '%%%s%%' % val)
        elif self.cond == '=':
            condition = lambda col: \
                lambda val: mapper.c[col] == utils.utf8(val)
        else:
            condition = lambda col: \
                lambda val: mapper.c[col].op(self.cond)(val)

        for col in properties:
            ors = or_(*list(map(condition(col), self.values.express())))
            result.update(query.filter(ors).all())

        if None in result:
            logger.warn('removing None from result set')
            result = set(i for i in result if i is not None)
        return result


class AggregatingAction(object):

    def __init__(self, t):
        logger.debug("AggregatingAction::__init__(%s)" % t)
        self.function = t[0]
        self.identifier = t[2]

    def __repr__(self):
        return "(%s %s)" % (self.function, self.identifier)

    def needs_join(self, env):
        return [self.identifier.needs_join(env)]

    def evaluate(self, env):
        """return pair (query, attribute)

        let the identifier compute the query and its attribute, we do
        not need alter anything right now since the condition on the
        aggregated identifier is applied in the HAVING and not in the
        WHERE.

        """

        return self.identifier.evaluate(env)


class ValueListAction(object):

    def __init__(self, t):
        logger.debug("ValueListAction::__init__(%s)" % t)
        self.values = t[0]

    def __repr__(self):
        return str(self.values)

    def express(self):
        return [i.express() for i in self.values]

    def invoke(self, search_strategy):
        """
        Called when the whole search string is a value list.

        Search with a list of values is the broadest search and
        searches all the mapper and the properties configured with
        add_meta()
        """

        logger.debug('ValueListAction:invoke')
        # make searches case-insensitive, in postgres use ilike,
        # in other use upper()
        like = lambda table, col, val: \
            utils.ilike(table.c[col], ('%%%s%%' % val))

        result = set()
        for cls, columns in search_strategy._properties.items():
            column_cross_value = [(c, v) for c in columns
                                  for v in self.express()]
            # as of SQLAlchemy>=0.4.2 we convert the value to a unicode
            # object if the col is a Unicode or UnicodeText column in order
            # to avoid the "Unicode type received non-unicode bind param"

            def unicol(col, v):
                table = class_mapper(cls)
                if isinstance(table.c[col].type, (Unicode, UnicodeText)):
                    return str(v)
                else:
                    return v

            table = class_mapper(cls)
            q = search_strategy._session.query(cls)  # prepares SELECT
            q = q.filter(or_(*[like(table, c, unicol(c, v))
                               for c, v in column_cross_value]))
            result.update(q.all())

        def replace(i):
            try:
                replacement = i.replacement()
                logger.debug('replacing %s by %s in result set' %
                             (i, replacement))
                return replacement
            except:
                return i
        result = set([replace(i) for i in result])
        logger.debug("result is now %s" % result)
        if None in result:
            logger.warn('removing None from result set')
            result = set(i for i in result if i is not None)
        return result


from pyparsing import (
    Word, alphas8bit, removeQuotes, delimitedList, Regex,
    ZeroOrMore, OneOrMore, oneOf, alphas, alphanums, Group, Literal,
    CaselessLiteral, WordStart, WordEnd, srange,
    stringEnd, Keyword, quotedString,
    infixNotation, opAssoc, Forward)

wordStart, wordEnd = WordStart(), WordEnd()


class SearchParser(object):
    """The parser for bauble.search.MapperSearch
    """

    numeric_value = Regex(
        r'[-]?\d+(\.\d*)?([eE]\d+)?'
        ).setParseAction(NumericToken)('number')
    unquoted_string = Word(alphanums + alphas8bit + '%.-_*;:')
    string_value = (
        quotedString.setParseAction(removeQuotes) | unquoted_string
        ).setParseAction(StringToken)('string')

    none_token = Literal('None').setParseAction(NoneToken)
    empty_token = Literal('Empty').setParseAction(EmptyToken)

    value_list = Forward()
    typed_value = (
        Literal("|") + unquoted_string + Literal("|") +
        value_list + Literal("|")
        ).setParseAction(TypedValueToken)

    value = (
        typed_value |
        WordStart('0123456789.-e') + numeric_value + WordEnd('0123456789.-e') |
        none_token |
        empty_token |
        string_value
        ).setParseAction(ValueToken)('value')
    value_list <<= Group(
        OneOrMore(value) ^ delimitedList(value)
        ).setParseAction(ValueListAction)('value_list')

    domain = Word(alphas, alphanums)
    binop = oneOf('= == != <> < <= > >= not like contains has ilike '
                  'icontains ihas is')
    binop_set = oneOf('in')
    equals = Literal('=')
    star_value = Literal('*')
    domain_values = (value_list.copy())('domain_values')
    domain_expression = (
        (domain + equals + star_value + stringEnd)
        | (domain + binop + domain_values + stringEnd)
        ).setParseAction(DomainExpressionAction)('domain_expression')

    caps = srange("[A-Z]")
    lowers = caps.lower()
    binomial_name = (
        Word(caps, lowers) + Word(lowers)
        ).setParseAction(BinomialNameAction)('binomial_name')

    AND_ = wordStart + (CaselessLiteral("AND") | Literal("&&")) + wordEnd
    OR_ = wordStart + (CaselessLiteral("OR") | Literal("||")) + wordEnd
    NOT_ = wordStart + (CaselessLiteral("NOT") | Literal('!')) + wordEnd
    BETWEEN_ = wordStart + CaselessLiteral("BETWEEN") + wordEnd

    aggregating_func = (Literal('sum') | Literal('min') | Literal('max')
                        | Literal('count'))

    query_expression = Forward()('filter')

    atomic_identifier = Word(alphas+'_', alphanums+'_')
    identifier = (
        Group(atomic_identifier + ZeroOrMore('.' + atomic_identifier) + '[' + atomic_identifier + binop + value + ']' + '.' + atomic_identifier).setParseAction(FilteredIdentifierAction)
        | Group(atomic_identifier + ZeroOrMore('.' + atomic_identifier)).setParseAction(IdentifierAction)
    )

    aggregated = (aggregating_func + Literal('(') + identifier + Literal(')')
                  ).setParseAction(AggregatingAction)
    ident_expression = (Group(identifier + binop + value
                              ).setParseAction(IdentExpression)
                        | Group(identifier + binop_set + value_list
                                ).setParseAction(ElementSetExpression)
                        | Group(aggregated + binop + value
                                ).setParseAction(AggregatedExpression)
                        | (Literal('(') + query_expression + Literal(')')
                           ).setParseAction(ParenthesisedQuery))
    between_expression = Group(
        identifier + BETWEEN_ + value + AND_ + value
        ).setParseAction(BetweenExpressionAction)
    query_expression <<= infixNotation(
        (ident_expression | between_expression),
        [(NOT_, 1, opAssoc.RIGHT, SearchNotAction),
         (AND_, 2, opAssoc.LEFT,  SearchAndAction),
         (OR_,  2, opAssoc.LEFT,  SearchOrAction)])
    query = (domain + Keyword('where', caseless=True).suppress() +
             Group(query_expression) + stringEnd).setParseAction(QueryAction)

    statement = (query('query')
                 | domain_expression('domain')
                 | binomial_name('binomial')
                 | value_list('value_list')
                 ).setParseAction(StatementAction)('statement')

    def parse_string(self, text):
        '''request pyparsing object to parse text

        `text` can be either a query, or a domain expression, or a list of
        values. the `self.statement` pyparsing object parses the input text
        and return a pyparsing.ParseResults object that represents the input
        '''

        return self.statement.parseString(text)


class SearchStrategy(object):
    """
    Interface for adding search strategies to a view.
    """

    def search(self, text, session=None):
        '''
        :param text: the search string
        :param session: the session to use for the search

        Return an iterator that iterates over mapped classes retrieved
        from the search.
        '''
        logger.debug('SearchStrategy "%s"(%s)' % (text, self.__class__.__name__))
        pass


class MapperSearch(SearchStrategy):

    """
    Mapper Search support three types of search expression:
    1. value searches: search that are just list of values, e.g. value1,
    value2, value3, searches all domains and registered columns for values
    2. expression searches: searched of the form domain=value, resolves the
    domain and searches specific columns from the mapping
    3. query searchs: searches of the form domain where ident.ident = value,
    resolve the domain and identifiers and search for value
    """

    _domains = {}
    _shorthand = {}
    _properties = {}

    def __init__(self):
        super().__init__()
        self._results = set()
        self.parser = SearchParser()

    def add_meta(self, domain, cls, properties):
        """Add a domain to the search space

        an example of domain is a database table, where the properties would
        be the table columns to consider in the search.  continuing this
        example, a record is be selected if any of the fields matches the
        searched value.

        :param domain: a string, list or tuple of domains that will resolve
                       a search string to cls.  domain act as a shorthand to
                       the class name.
        :param cls: the class the domain will resolve to
        :param properties: a list of string names of the properties to
                           search by default
        """

        logger.debug('%s.add_meta(%s, %s, %s)' %
                     (self, domain, cls, properties))

        check(isinstance(properties, list),
              _('MapperSearch.add_meta(): '
                'default_columns argument must be list'))
        check(len(properties) > 0,
              _('MapperSearch.add_meta(): '
                'default_columns argument cannot be empty'))
        if isinstance(domain, (list, tuple)):
            self._domains[domain[0]] = cls, properties
            for d in domain[1:]:
                self._shorthand[d] = domain[0]
        else:
            self._domains[domain] = cls, properties
        self._properties[cls] = properties

    @classmethod
    def get_domain_classes(cls):
        d = {}
        for domain, item in cls._domains.items():
            d.setdefault(domain, item[0])
        return d

    def search(self, text, session=None):
        """
        Returns a set() of database hits for the text search string.

        If session=None then the session should be closed after the results
        have been processed or it is possible that some database backends
        could cause deadlocks.
        """
        super().search(text, session)
        self._session = session

        self._results.clear()
        statement = self.parser.parse_string(text).statement
        logger.debug("statement : %s(%s)" % (type(statement), statement))
        self._results.update(statement.invoke(self))
        logger.debug('search returns %s(%s)'
                     % (type(self._results), self._results))

        # these _results get filled in when the parse actions are called
        return self._results


## list of search strategies to be tried on each search string
_search_strategies = {'MapperSearch': MapperSearch()}


def add_strategy(strategy):
    obj = strategy()
    _search_strategies[obj.__class__.__name__] = obj


def get_strategy(name):
    return _search_strategies.get(name, None)


class SchemaBrowser(Gtk.VBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.props.spacing = 10
        # WARNING: this is a hack from MapperSearch
        self.domain_map = MapperSearch.get_domain_classes().copy()

        frame = Gtk.Frame(_("Search Domain"))
        self.pack_start(frame, False, False, 0)
        self.table_combo = Gtk.ComboBoxText()
        frame.add(self.table_combo)
        for key in sorted(self.domain_map.keys()):
            self.table_combo.append_text(key)

        self.table_combo.connect('changed', self.on_table_combo_changed)

        self.prop_tree = Gtk.TreeView()
        self.prop_tree.set_headers_visible(False)
        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Property"), cell)
        self.prop_tree.append_column(column)
        column.add_attribute(cell, 'text', 0)

        self.prop_tree.connect('test_expand_row', self.on_row_expanded)

        frame = Gtk.Frame(_('Domain Properties'))
        sw = Gtk.ScrolledWindow()
        sw.add(self.prop_tree)
        frame.add(sw)
        self.pack_start(frame, True, True, 0)

    def _insert_props(self, mapper, model, treeiter):
        """
        Insert the properties from mapper into the model at treeiter
        """
        column_properties = sorted(
            [x for x in mapper.iterate_properties if isinstance(x, ColumnProperty)
                   and not x.key.startswith('_')],
            key=lambda k: (k.key!='id', not k.key.endswith('_id'), k.key))
        for prop in column_properties:
            model.append(treeiter, [prop.key, prop])

        relation_properties = sorted(
            [x for x in mapper.iterate_properties if isinstance(x, RelationProperty)
                   and not x.key.startswith('_')],
            key=lambda k: k.key)
        for prop in relation_properties:
            it = model.append(treeiter, [prop.key, prop])
            model.append(it, ['', None])

    def on_row_expanded(self, treeview, treeiter, path):
        """
        Called before the row is expanded and populates the children of the
        row.
        """
        logger.debug('on_row_expanded')
        model = treeview.props.model
        parent = treeiter
        while model.iter_has_child(treeiter):
            nkids = model.iter_n_children(parent)
            child = model.iter_nth_child(parent, nkids-1)
            model.remove(child)

        # prop should always be a RelationProperty
        prop = treeview.props.model[treeiter][1]
        self._insert_props(prop.mapper, model, treeiter)

    def on_table_combo_changed(self, combo, *args):
        """
        Change the table to use for the query
        """
        utils.clear_model(self.prop_tree)
        it = combo.get_active_iter()
        domain = combo.props.model[it][0]
        mapper = class_mapper(self.domain_map[domain])
        model = Gtk.TreeStore(str, object)
        root = model.get_iter_root()
        self._insert_props(mapper, model, root)
        self.prop_tree.props.model = model

