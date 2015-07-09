# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

import unittest
from bauble import search
plants = __import__("bauble.plugins", globals(), locals(), ['plants'], -1).plants

from pyparsing import ( alphas, alphas8bit, alphanums, Group, Literal, CaselessLiteral, Word, Keyword, quotedString,
                        removeQuotes, OneOrMore, infixNotation, stringEnd, opAssoc, oneOf, delimitedList, Regex ) 

from sqlalchemy import and_, or_, not_

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
from sqlalchemy import Column, Integer, String, ForeignKey


class Family(Base):
    __tablename__ = 'family'
    id = Column(Integer, primary_key=True)
    family = Column(String(45), nullable=False, index=True)


class Genus(Base):
    __tablename__ = 'genus'
    id = Column(Integer, primary_key=True)
    genus = Column(String(64), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey('family.id'), nullable=False)


class Species(Base):
    __tablename__ = 'species'
    id = Column(Integer, primary_key=True)
    sp = Column(String(64), nullable=False, index=True)
    genus_id = Column(Integer, ForeignKey('genus.id'), nullable=False)

###############################################################################
## the following code is what is being tested. I'm developing it here, but
## eventually it will be part of bauble

class UnaryLogical(object):
    ## op is the textual operator, while operator, defined in derived class,
    ## is the function implementing the operation.
    def __init__(self, t):
        self.op, self.operand = t[0]

    def __repr__(self):
        return "%s %s" % (self.op, str(self.operand))    

    def express(self, env):
        return self.operator(self.operand.express())

class BinaryLogical(object):
    ## op is the textual operator, while operator, defined in derived class,
    ## is the function implementing the operation.
    def __init__(self, t):
        self.op = t[0][1]
        self.operands = t[0][0::2]  # every second object is an operand

    def __repr__(self):
        return "(%s %s %s)" % (self.operands[0], self.name, self.operands[1])

    def express(self, env):
        return self.operator(*( oper.express() for oper in self.operands ))    

class StringAction(object):
    ## op is the textual operator, while operator, defined in derived class,
    ## is the function implementing the operation.
    def __init__(self, t):
        self.value = t[0]

    def __repr__(self):
        return "'%s'" % ( self.value )

    def express(self, env):
        return self.value

class NumericFloatAction(object):
    ## op is the textual operator, while operator, defined in derived class,
    ## is the function implementing the operation.
    def __init__(self, t):
        self.value = float(t[0])

    def __repr__(self):
        return "%s" % ( self.value )

    def express(self, env):
        return self.value

class NumericIntegerAction(object):
    ## op is the textual operator, while operator, defined in derived class,
    ## is the function implementing the operation.
    def __init__(self, t):
        self.value = int(t[0])

    def __repr__(self):
        return "%s" % ( self.value )

    def express(self, env):
        return self.value

class IdentifierAction(object):
    def __init__(self, t):
        self.value = '.'.join(t[0])

    def __repr__(self):
        return "%s" % ( self.value )

    def express(self, env):
        return self.value

class IdentExpressionAction(object):
    ## op is the textual operator, while operator, defined in derived class,
    ## is the function implementing the operation.
    def __init__(self, t):
        self.op = t[0][1]
        self.operation = {'>': lambda x,y: x>y,
                          '<': lambda x,y: x<y,
                          '>=': lambda x,y: x>=y,
                          '<=': lambda x,y: x<=y,
                          '=': lambda x,y: x==y,
                          '!=': lambda x,y: x!=y,
                      }[self.op]
        self.operands = t[0][0::2]  # every second object is an operand

    def __repr__(self):
        return "(%s %s %s)" % ( self.operands[0], self.op, self.operands[1])

    def express(self, env):
        return self.operation(*[oper.express(env) for oper in self.operands])    

class SearchAndAction(BinaryLogical):
    name = 'AND'
    operator = and_

class SearchOrAction(BinaryLogical):
    name = 'OR'
    operator = or_

class SearchNotAction(UnaryLogical):
    name = 'NOT'
    operator = not_

class QueryAction(object):
    def __init__(self, t):
        self.domain = t[0]
        self.filter = t[1][0]

    def __repr__(self):
        return "SELECT * FROM %s WHERE %s" % ( self.domain, self.filter )

    def express(self, env):
        return self.filter.express(env)

class StatementAction(object):
    def __init__(self, t):
        print t, [type(i) for i in t]
        self.query = t[0]
        print type(self.query)

    def __repr__(self):
        return repr(self.query)

    def express(self, env):
        return self.query.express(env)

def domain_expression_action(*args):
    print 'd:', args, [type(i) for i in args]

def value_list_action(*args):
    print 'v:', args, [type(i) for i in args]

integer_value = Regex(r'[-]?\d+').setParseAction(NumericIntegerAction)
float_value = Regex(r'[-]?\d+(\.\d*)?([eE]\d+)?').setParseAction(NumericFloatAction)
value_chars = Word(alphas + alphas8bit, alphanums + alphas8bit + '%.-_*;:')
string_value = (value_chars | quotedString.setParseAction(removeQuotes)).setParseAction(StringAction)
# value can contain any string once its quoted

value = string_value | integer_value | float_value
value_list = (string_value ^ delimitedList(string_value) ^ OneOrMore(string_value))

binop = oneOf('= == != <> < <= > >= not like contains has ilike '
              'icontains ihas is').setName('binop')
domain = Word(alphas, alphanums).setName('domain')
domain_values = Group(value_list.copy())
domain_expression = (domain + Literal('=') + Literal('*') + stringEnd) \
                    | (domain + binop + domain_values + stringEnd)

AND_ = CaselessLiteral("and")
OR_  = CaselessLiteral("or")
NOT_ = CaselessLiteral("not") | Literal('!')

identifier = Group(delimitedList(Word(alphas, alphanums+'_'), '.')).setParseAction(IdentifierAction)
ident_expression = Group(identifier + binop + value).setParseAction(IdentExpressionAction)
query_expression = infixNotation( 
    ident_expression,
    [ (NOT_, 1, opAssoc.RIGHT, SearchNotAction),
      (AND_, 2, opAssoc.LEFT,  SearchAndAction),
      (OR_,  2, opAssoc.LEFT,  SearchOrAction) ] )
query = (domain + Keyword('where', caseless=True).suppress() + 
         Group(query_expression) + stringEnd)

statement = (query.setParseAction(QueryAction)('query')
             | domain_expression.setParseAction(domain_expression_action)('domain')
             | value_list.setParseAction(value_list_action)('values')
         ).setParseAction(StatementAction)('statement')


###############################################################################
## the following 'search' object exposes the interface that will be
## implemented by the code that eventually will be part of bauble

class Search(object):
    def get_strategy(self, session):
        self.session = session
        return self

    def search(self, q):
        return statement.parseString(q)

Search.MapperSearch = Search

search = Search()

###############################################################################
## here the testing logic

class SearchStrategyTest(unittest.TestCase):
    """test cases based on in-memory data
    """

    def __init__(self, *args):
        super(SearchStrategyTest, self).__init__(*args)

        from sqlalchemy import create_engine
        engine = create_engine('sqlite:///:memory:', echo=True)

        Base.metadata.create_all(engine) 

        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        self.session = Session()

        family1 = Family(id=1, family=u'family1')
        family2 = Family(id=2, family=u'family2')
        genus1 = Genus(id=1, family_id=1, genus=u'genus1')
        genus2 = Genus(id=2, family_id=2, genus=u'genus2')
        species11 = Species(id=1, genus_id=1, sp=u's1.1.2')
        species12 = Species(id=2, genus_id=1, sp=u's1.1.2')
        species21 = Species(id=3, genus_id=2, sp=u's2.2.1')
        species22 = Species(id=4, genus_id=2, sp=u's2.2.2')
        self.session.add_all([family1, family2, genus1, genus2, species11, species12, species21, species22])
        self.session.commit()
        self.test_species = species21

    def test_database_was_created(self):
        "test the database was initialised"

        # our_user = self.session.query(getattr(locals(), 'Species')).filter_by(sp=u's2.2.1').first() 
        our_user = self.session.query(Species).filter_by(sp=u's2.2.1').first() 
        self.assertEqual(our_user, self.test_species)

    def test_find_correct_strategy(self):
        "verify the MapperSearch strategy is available"

        mapper_search = search.get_strategy('MapperSearch')
        self.assertTrue(isinstance(mapper_search, search.MapperSearch))

    def test_canfindspeciesfromgenus(self):
        'can find species from genus'

        mapper_search = search.get_strategy('MapperSearch')
        results = mapper_search.search('species where species.genus=genus1')
        print dir(results)
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE (species.genus = 'genus1')")

    def test_canuselogicaloperators(self):
        'can use logical operators'

        mapper_search = search.get_strategy('MapperSearch')
        results = mapper_search.search('species where species.genus=genus1 or species.sp=name and species.genus.family.family=name')
        self.assertEqual(str(results.statement), "SELECT * FROM species WHERE ((species.genus = 'genus1') OR ((species.sp = 'name') AND (species.genus.family.family = 'name')))")

    def test_canfindfamilyfromgenus(self):
        'can find family from genus'

        mapper_search = search.get_strategy('MapperSearch')
        results = mapper_search.search('family where family.genus=genus1')
        self.assertEqual(str(results.statement), "SELECT * FROM family WHERE (family.genus = 'genus1')")

    def test_canfindgenusfromfamily(self):
        'can find genus from family'

        mapper_search = search.get_strategy('MapperSearch')
        results = mapper_search.search('genus where genus.family=family2')
        print dir(plants)
        print 1, results, type(results)
        print 2, results.statement
        print 3, results.statement.query.filter.express(self.session)
        self.assertEqual(str(results.statement), "SELECT * FROM genus WHERE (genus.family = 'family2')")

    def test_canfindplantbyaccession(self):
        'can find plant from the accession id'

        mapper_search = search.get_strategy('MapperSearch')
        results = mapper_search.search('plant where accession.species.id=113')
        self.assertEqual(str(results.statement), 'SELECT * FROM plant WHERE (accession.species.id = 113)')
