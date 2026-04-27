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
import logging
from datetime import date, datetime, timedelta
from gettext import gettext as _
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    Union,
    runtime_checkable,
)

import bauble.utils as utils

# from bauble.db import get_orm_entity_by_name
from bauble.error import check
from bauble.gtkinit import Gtk
from pyparsing import (
    CaselessKeyword,
    CaselessLiteral,
    DelimitedList,
    Forward,
    Group,
    Keyword,
    Literal,
    MatchFirst,
    OneOrMore,
    OpAssoc,
    ParserElement,
    ParseResults,
    Regex,
    Word,
    WordEnd,
    WordStart,
    ZeroOrMore,
    alphanums,
    alphas,
    alphas8bit,
    infix_notation,
    one_of,
    quotedString,
    removeQuotes,
    srange,
    stringEnd,
)

# Core SQLAlchemy
from sqlalchemy import and_, func, inspect, or_, select

# Errors
from sqlalchemy.exc import NoResultFound

# ORM-specific
from sqlalchemy.orm import (
    ColumnProperty,
    DeclarativeMeta,
    RelationshipProperty,
    Session,
    aliased,
)
from sqlalchemy.orm.util import AliasedClass
from sqlalchemy.sql.selectable import Select

logger: logging.Logger = logging.getLogger(__name__)
wordStart: ParserElement
wordEnd: ParserElement




logger.setLevel(logging.INFO)


RelationProperty = RelationshipProperty


from sqlalchemy.orm import RelationshipProperty


def resolve_relationships(
    cls: Any, steps: List[str], env: Dict[str, Any]
) -> Tuple[Select, Any]:
    """
    Dynamically resolve relationships for a given class and steps.

    Args:
        cls: The current SQLAlchemy class being evaluated.
        steps: A list of relationship steps to resolve.
        env: The environment containing the session and other context.

    Returns:
        (stmt, current_cls): The updated statement and the final resolved class.
    """
    if not steps:
        raise ValueError("No relationship steps provided to resolve.")

    stmt = select(cls)  # Start with the base class
    current_cls = cls

    for step in steps:
        # Ensure we are inspecting the mapper of current_cls
        mapper = (
            inspect(current_cls).mapper
            if isinstance(current_cls, AliasedClass)
            else inspect(current_cls)
        )

        # Retrieve the relationship property
        if step not in mapper.relationships:
            raise ValueError(
                f"Relationship '{step}' not found on '{current_cls.__name__}'. Available: {list(mapper.relationships.keys())}"
            )

        relationship_property = mapper.relationships[step]
        if not relationship_property:
            raise ValueError(
                f"Relationship '{step}' not found on '{current_cls.__name__}'."
            )

        # Resolve target class and alias it
        target_cls = relationship_property.mapper.class_
        if not target_cls:
            raise ValueError(
                f"Unable to resolve target class for relationship '{step}'."
            )

        aliased_entity = aliased(target_cls)
        stmt = stmt.join(aliased_entity, getattr(current_cls, step))
        current_cls = aliased_entity  # Update for next steps

    return stmt, current_cls



def _accepts_seed(strategy):
    try:
        sig = inspect.signature(strategy.search)
        return 'seed' in sig.parameters
    except Exception:
        return False

def search(text: str, session: Optional[Session] = None) -> List[Any]:
    results: Set[Any] = set()

    # Run MapperSearch first to get the base results exactly once
    mapper = _search_strategies.get("MapperSearch")
    base: Set[Any] = set()
    if mapper is not None:
        base = set(mapper.search(text, session))
        results.update(base)

    # Other strategies can use the base as a seed (no re-running MapperSearch)
    for name, strategy in _search_strategies.items():
        if name == "MapperSearch":
            continue
        try:
            if _accepts_seed(strategy):
                out = strategy.search(text, session, seed=base)
            else:
                out = strategy.search(text, session)
            if out:
                results.update(out)       
        except Exception:
            logger.exception("Search strategy %s failed", strategy.__class__.__name__)

    return list(results)


class NoneToken:
    def __init__(self, t: Optional[Any] = None) -> None:
        pass

    def __repr__(self) -> str:
        return "(None<NoneType>)"

    def express(self) -> None:
        return None


class EmptyToken:
    def __init__(self, t: Optional[Any] = None) -> None:
        pass

    def __repr__(self) -> str:
        return "Empty"

    def express(self) -> Set[Any]:
        return set()

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, EmptyToken):
            return True
        if isinstance(other, set):
            return len(other) == 0
        return NotImplemented


class ValueABC:
    # abstract base class.
    value: Any  # Explicitly declare type

    def express(self) -> Any:
        return self.value


class ValueToken:

    value: Any

    def __init__(self, t: Any) -> None:
        self.value = t[0]

    def __repr__(self) -> str:
        return repr(self.value)

    def express(self) -> Any:
        return self.value.express()


class StringToken(ValueABC):
    value: Any

    def __init__(self, t: Any) -> None:
        self.value = t[0]  # no need to parse the string

    def __repr__(self) -> str:
        return f"'{self.value}'"


class NumericToken(ValueABC):
    value: Any

    def __init__(self, t: Any) -> None:
        self.value = float(t[0])  # store the float value

    def __repr__(self) -> str:
        return f"{self.value}"


def smartdatetime(year_or_offset: int, *args: int) -> datetime:
    """return either datetime.datetime, or a day with given offset.

    When given only one argument, this is interpreted as an offset for
    timedelta, and it is added to datetime.today().  If given more
    arguments, it just behaves as datetime.datetime.

    """
    from datetime import datetime as dt

    if not args:
        return dt.today().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=year_or_offset)
    else:
        return dt(year_or_offset, *(args[:5]))  # type: ignore[arg-type]


def smartboolean(*args: Union[str, float, int]) -> bool:
    """translate args into boolean value

    Result is True whenever first argument is not numerically zero nor
    literally 'false'.  No arguments cause error.

    """
    if len(args) == 1:
        try:
            return float(args[0]) != 0.0
        except (ValueError, TypeError):
            return str(args[0]).lower() != "false"
    return True


class TypedValueToken(ValueABC):
    # |<name>|<paramlist>|
    value: Any
    constructor: Dict[str, Tuple[Callable[..., Any], type]] = {
        "datetime": (smartdatetime, int),
        "bool": (smartboolean, str),
    }

    def __init__(self, t: Any) -> None:
        logger.debug(f"constructing typedvaluetoken {str(t)}")
        try:
            constructor, converter = self.constructor[t[1]]
        except KeyError:
            return
        params = tuple(converter(i) for i in t[3].express())
        self.value = constructor(*params)

    def __repr__(self) -> str:
        return f"{self.value}"


class IdentifierAction:
    steps: List[str]
    leaf: str

    def __init__(self, t: Any) -> None:
        logger.debug(f"IdentifierAction::__init__({t})")
        self.steps = t[0][:-2:2]
        self.leaf = t[0][-1]

    def __repr__(self) -> str:
        return ".".join(self.steps + [self.leaf])

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """
        Return a pair (stmt, attribute) where stmt is a SQLAlchemy 2.0 select()
        that will return full ORM objects.
        """
        # Handle both dictionary and object-style `env`
        domain_class: Any = getattr(env, "domain", None) or env.get("domain", None)
        getattr(env, "session", None) or env.get("session", None)
        search_strategy: Any = getattr(env, "search_strategy", None) or env.get(
            "search_strategy", None
        )

        if not domain_class:
            raise ValueError("Invalid or missing domain class in env")

        # If domain_class is a string, resolve it
        if isinstance(domain_class, str) and search_strategy:
            domain_class = search_strategy._domains.get(domain_class, [None])[0]
            if not domain_class:
                raise ValueError(
                    f"Unknown domain: '{domain_class}' not found in registered domains."
                )

        # Ensure domain_class is an ORM-mapped class
        if not inspect(domain_class, raiseerr=False):
            raise TypeError(
                f"Expected ORM class, got {type(domain_class)} instead: {domain_class}"
            )

        # Construct SQL query using ORM class
        stmt: Select = select(domain_class)
        current_cls: Any = domain_class

        # Handle joins if steps exist
        if self.steps:
            for step in self.steps:
                if not hasattr(current_cls, step):
                    raise ValueError(
                        f"Relationship '{step}' not found in '{current_cls.__name__}'"
                    )
                rel_attr = getattr(current_cls, step)
                related_cls = rel_attr.property.mapper.class_

                aliased_entity = aliased(related_cls)
                stmt = stmt.join(aliased_entity, rel_attr)
                current_cls = aliased_entity  # Move to the next step

        # Retrieve the final attribute
        try:
            attr = getattr(current_cls, self.leaf)
        except AttributeError:
            raise ValueError(
                f"Attribute '{self.leaf}' not found on class '{current_cls.__name__}'"
            )

        return stmt, attr

    def needs_join(self, env: Any) -> Any:
        return self.steps or []


# class IdentifierAction(object):
#     def __init__(self, t):
#         logger.debug("IdentifierAction::__init__(%s)" % t)
#         self.steps = t[0][:-2:2]
#         self.leaf = t[0][-1]

#     def __repr__(self):
#         return ".".join(self.steps + [self.leaf])
#     from sqlalchemy.orm import Session  # ✅ Ensure Session is imported
#     import inspect  # ✅ To check if an object is a class

#     def evaluate(self, env):
#         """
#         Return pair (stmt, attribute) where stmt is a SQLAlchemy 2.0 select()
#         that will return full ORM objects.
#         """
#         # ✅ Extract domain_class from env
#         domain_class = env.get("domain", None)
#         search_strategy = env.get("search_strategy", None)  # ✅ Ensure this is not a Session

#         print(f"DEBUG: IdentifierAction.evaluate() called with domain_class='{domain_class}' ({type(domain_class)})")
#         print(f"DEBUG: search_strategy type -> {type(search_strategy)}")

#         if not domain_class:
#             raise ValueError("Invalid or missing domain class")
#         from sqlalchemy.orm import Session
#         # ✅ Ensure search_strategy is NOT a Session but an actual search strategy
#         if isinstance(search_strategy, Session):
#             raise TypeError(
#                 "search_strategy should not be a SQLAlchemy Session, but an instance of MapperSearch or similar."
#             )

#         from sqlalchemy.orm import DeclarativeMeta  # Import SQLAlchemy ORM class type
#         from sqlalchemy.orm import registry

#         # Get the base registry used for mapping
#         mapper_registry = registry()

#         # ✅ Convert domain name string into ORM class if necessary
#         if isinstance(domain_class, str):
#             if hasattr(search_strategy, "_domains"):
#                 resolved_class = search_strategy._domains.get(domain_class)
#                 if not resolved_class:
#                     raise ValueError(f"Unknown domain: '{domain_class}' not found in registered domains.")
#                 domain_class = resolved_class[0]  # Extract first match
#             else:
#                 raise AttributeError(
#                     "search_strategy does not have '_domains'. Ensure correct initialization of MapperSearch."
#                 )

#         # ✅ Ensure domain_class is a SQLAlchemy ORM-mapped class
#         if not isinstance(domain_class, type) or not issubclass(domain_class, DeclarativeMeta):
#             raise TypeError(f"Expected ORM class, got {type(domain_class)} instead: {domain_class}")

#         # ✅ Check if class is actually mapped by SQLAlchemy
#         if domain_class not in mapper_registry.mappers:
#             raise TypeError(f"Class {domain_class} is not mapped with SQLAlchemy.")

#         # ✅ Construct SQL query using ORM class
#         if not self.steps:
#             stmt = select(domain_class)
#             current_cls = domain_class
#         else:
#             current_cls = aliased(domain_class)
#             relationships = [
#                 getattr(current_cls, step) if isinstance(step, str) else step
#                 for step in self.steps
#             ]
#             stmt = select(current_cls).join(*relationships)

#         try:
#             attr = getattr(current_cls, self.leaf)
#         except AttributeError:
#             raise ValueError(f"Attribute '{self.leaf}' not found on class '{current_cls}'.")

#         print(f"DEBUG: Resolved attribute -> {attr}")

#         return stmt, attr

#     def needs_join(self, env):
#         return self.steps or []


class FilteredIdentifierAction:
    steps: List[str]
    filter_attr: str
    filter_op: str
    filter_value: Any
    leaf: str
    operation: Optional[Callable[[Any, Any], Any]]

    def __init__(self, t: Any) -> None:
        logger.debug(f"FilteredIdentifierAction::__init__({t})")
        self.steps = t[0][:-7:2]
        self.filter_attr = t[0][-6]
        self.filter_op = t[0][-5]
        self.filter_value = t[0][-4]
        self.leaf = t[0][-1]

        # cfr: SearchParser.binop
        # = == != <> < <= > >= not like contains has ilike icontains ihas is
        self.operation = {
            "=": lambda x, y: x == y,
            "==": lambda x, y: x == y,
            "is": lambda x, y: x == y,
            "!=": lambda x, y: x != y,
            "<>": lambda x, y: x != y,
            "not": lambda x, y: x != y,
            "<": lambda x, y: x < y,
            "<=": lambda x, y: x <= y,
            ">": lambda x, y: x > y,
            ">=": lambda x, y: x >= y,
            "like": lambda x, y: utils.ilike(x, f"{y}"),
            "contains": lambda x, y: utils.ilike(x, f"%{y}%"),
            "has": lambda x, y: utils.ilike(x, f"%{y}%"),
            "ilike": lambda x, y: utils.ilike(x, f"{y}"),
            "icontains": lambda x, y: utils.ilike(x, f"%{y}%"),
            "ihas": lambda x, y: utils.ilike(x, f"%{y}%"),
        }.get(self.filter_op)

    def __repr__(self) -> str:
        return "{}[{}{}{}].{}".format(
            ".".join(self.steps),
            self.filter_attr,
            self.filter_op,
            self.filter_value,
            self.leaf,
        )

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """
        Evaluate the identifier and return the query and attribute.
        """
        # Use resolve_relationships to dynamically resolve steps
        stmt, current_cls = resolve_relationships(env["domain"], self.steps, env)
        if stmt is None or current_cls is None:
            raise ValueError(f"Failed to resolve relationships for steps: {self.steps}")

        # Verify that the class has the filter column
        if not hasattr(current_cls, self.filter_attr):
            raise ValueError(
                f"Attribute '{self.filter_attr}' not found on '{current_cls}'"
            )
        attr = getattr(current_cls, self.filter_attr)

        if self.operation is None:
            raise ValueError(f"Unsupported filter operation: {self.filter_op}")

        op = self.operation  # type: Callable[[Any, Any], Any]

        def clause(x: Any) -> Any:
            return op(attr, x)

        stmt = stmt.filter(clause(self.filter_value.express()))

        # Resolve the final leaf attribute
        leaf_attr = getattr(current_cls, self.leaf, None)
        if not leaf_attr:
            raise ValueError(
                f"Leaf attribute '{self.leaf}' not found on '{current_cls}'"
            )

        return stmt, leaf_attr

    def needs_join(self, env: Any) -> List[Any]:
        return self.steps


class IdentExpression:
    op: ParserElement
    operation: Optional[Callable[[Any, Any], Any]]
    operands: List[Any]

    def __init__(self, t: Any) -> None:
        logger.debug(f"IdentExpression::__init__({t})")
        self.op = t[0][1]

        # cfr: SearchParser.binop
        # = == != <> < <= > >= not like contains has ilike icontains ihas is
        self.operation = {
            "=": lambda x, y: x == y,
            "==": lambda x, y: x == y,
            "is": lambda x, y: x == y,
            "is not": lambda x, y: x != y,
            "!=": lambda x, y: x != y,
            "<>": lambda x, y: x != y,
            "not": lambda x, y: x != y,
            "<": lambda x, y: x < y,
            "<=": lambda x, y: x <= y,
            ">": lambda x, y: x > y,
            ">=": lambda x, y: x >= y,
            "like": lambda x, y: utils.ilike(x, f"{y}"),
            "contains": lambda x, y: utils.ilike(x, f"%{y}%"),
            "has": lambda x, y: utils.ilike(x, f"%{y}%"),
            "ilike": lambda x, y: utils.ilike(x, f"{y}"),
            "icontains": lambda x, y: utils.ilike(x, f"%{y}%"),
            "ihas": lambda x, y: utils.ilike(x, f"%{y}%"),
        }.get(str(self.op))
        self.operands = t[0][0::2]  # every second object is an operand

    def __repr__(self) -> str:
        return f"({self.operands[0]} {self.op} {self.operands[1]})"



    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """
        Evaluate and return the filtered query result.
        """
        stmt: Select
        attr: Any

        # Unpack the query and attribute from the first operand
        stmt, attr = self.operands[0].evaluate(env)

        # Ensure correct column name from the ORM model
        column_name = getattr(attr, "key", None) or attr.name

        # Debugging step
        print(f"🔍 Evaluating Column: {column_name} in table {attr.parent}")

        session = getattr(env, "session", None) or env.get("session", None)

        if session and session.bind:
            print(
                "IdentExpression stmt:",
                stmt.compile(
                    dialect=session.bind.dialect, compile_kwargs={"literal_binds": True}
                ),
            )

        # Ensure self.operands[1] contains a valid value
        comparison_value = self.operands[1].express()

        # 🔍 Fix: Unwrap None if it's inside a list
        if isinstance(comparison_value, list) and len(comparison_value) == 1:
            comparison_value = comparison_value[0]

        # ✅ Normalize None and empty strings (for cross-database compatibility)
        # if isinstance(comparison_value, str) and comparison_value.lower().strip() in {"", "none"}:
        #    print(f"🔍 Normalizing '{comparison_value}' to None (Cross-DB Compatibility)")
        #    comparison_value = None  # Convert empty strings and "none" to None
        if isinstance(comparison_value, str) and comparison_value.strip() == "":
            print(
                f"🔍 Normalizing '{comparison_value}' to both '' and None (Cross-DB Compatibility)"
            )
            is_null_check = (
                True  # Mark that we need to check both NULL and empty string
            )
            comparison_value = None
        else:
            is_null_check = False

        if not isinstance(
            comparison_value, (str, int, float, bool, type(None), datetime, date)
        ):
            raise ValueError(f"Invalid comparison value: {comparison_value}")

        print(
            f"\n🔍 Evaluating: {attr} {self.op} {comparison_value} ({type(comparison_value)})"
        )

        # Debug: Fetch & Print Database Column Values Before Filtering
        print("\n🔍 Fetching Current Column Values Before Filtering:")

        # Instead of `attr.parent.table.name`, use the correct mapped class
        parent_cls = inspect(attr.parent).class_
        parent_inspect = inspect(parent_cls)
        table_name = (
            parent_inspect.persist_selectable.name
            if hasattr(parent_inspect, "persist_selectable")
            and parent_inspect.persist_selectable is not None
            else None
        )
        from sqlalchemy import text

        if session and table_name:
            try:
                dbg_stmt = text(f"SELECT id, {column_name} FROM {table_name}")
                query_result = (
                    session.execute(dbg_stmt).mappings().all()
                )  # ⬅️ Use .mappings()
                for row in query_result:
                    print(
                        f"🔍 DB Check: {column_name} = {row[column_name]} (Type: {type(row[column_name])})"
                    )
            except Exception as e:
                print(f"⚠️ Error fetching column data for debugging: {e}")

        # Check if the attribute is a relationship (i.e., a foreign key relationship)
        if isinstance(attr.property, RelationshipProperty):
            if comparison_value is None or comparison_value == "":
                if self.op in ("is", "=", "=="):
                    return (
                        stmt.filter(or_(attr.is_(None), attr == "")),
                        attr,
                    )  # ✅ WHERE author IS NULL
                elif self.op in ("is not", "not", "<>", "!="):
                    return (
                        stmt.filter(and_(attr.is_not(None), attr != "")),
                        attr,
                    )  # ✅ WHERE author IS NOT NULL

            elif self.operands[1].express() == set():
                if self.op in ("is", "=", "=="):
                    return stmt.filter(~attr.any()), attr  # No matching values
                elif self.op in ("is not", "not", "<>", "!="):
                    return stmt.filter(attr.any()), attr  # At least one matching value

        # # ✅ Fix: Ensure `None` is correctly handled
        # if comparison_value is None or comparison_value == "None":
        #     if self.op in ('is', '=', '=='):
        #         stmt = stmt.filter(attr.is_(None))  # ✅ Convert to SQL NULL
        #     elif self.op in ('is not', 'not', '<>', '!='):
        #         stmt = stmt.filter(attr.is_not(None))  # ✅ Convert to SQL NULL check
        # else:
        #     clause = lambda x: self.operation(attr, x)

        #     stmt = stmt.filter(clause(comparison_value))

        # ✅ Fix: Ensure `None` and `""` are correctly handled
        if is_null_check:
            # Special case: If filtering for an empty string, check for both NULL and ""
            if self.op in ("is", "=", "=="):
                stmt = stmt.filter(or_(attr.is_(None), attr == ""))
            elif self.op in ("is not", "not", "<>", "!="):
                stmt = stmt.filter(and_(attr.is_not(None), attr != ""))
        elif (
            comparison_value is None
            or comparison_value == "None"
            or comparison_value == ""
        ):
            if self.op in ("is", "=", "=="):
                stmt = stmt.filter(
                    or_(attr.is_(None), attr == "")
                )  # ✅ Convert to SQL NULL
            elif self.op in ("is not", "not", "<>", "!="):
                stmt = stmt.filter(
                    and_(attr.is_not(None), attr != "")
                )  # ✅ Convert to SQL NULL check
        else:
            if self.operation is None:
                raise ValueError(f"Unsupported filter operation: {self.op}")

            op = self.operation  # type: Callable[[Any, Any], Any]

            def clause(x: Any) -> Any:
                return op(attr, x)

            stmt = stmt.filter(clause(comparison_value))
        print(
            "Updated IdentExpression stmt:",
            stmt.compile(
                dialect=session.bind.dialect, compile_kwargs={"literal_binds": True}
            ),
        )
        return stmt, attr

    def needs_join(self, env: Dict[str, Any]) -> List[Any]:
        """
        Collect join steps from operands, ensuring a flat list.
        """
        return [self.operands[0].needs_join(env)]


class ElementSetExpression(IdentExpression):
    # currently only implements `in`

    # def evaluate(self, env):
    #     q, a = self.operands[0].evaluate(env)

    #     # Ensure 'q' is turned into a subquery
    #     #if not isinstance(q, AliasedClass):
    #     #    q = q.subquery()
    #     q = q.subquery()

    #     stmt = select(q).where(a.in_(self.operands[1].express()))
    #     return env.session.scalars(stmt)

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """
        Evaluates the IdentExpression and returns a statement and attribute.

        Ensures that the returned statement is correctly structured for SQLAlchemy 2.0,
        avoiding unnecessary subqueries while maintaining proper filtering behavior.
        """
        # Evaluate the first operand to get the base statement and attribute
        stmt, attr = self.operands[0].evaluate(env)

        # Ensure the session is available
        session = getattr(env, "session", None) or env.get("session", None)
        if not session:
            raise ValueError("Session is required for query execution.")

        # Ensure the second operand evaluates to a valid comparison value
        comparison_value = self.operands[1].express()
        if not isinstance(comparison_value, (str, int, float, bool, list, tuple, set)):
            raise ValueError(f"Invalid comparison value: {comparison_value}")

        # Apply filtering directly if stmt is already a select() statement
        if isinstance(stmt, select):
            stmt = stmt.where(attr.in_(comparison_value))
        else:
            stmt = select(stmt).where(attr.in_(comparison_value))

        return stmt, attr


class AggregatedExpression(IdentExpression):
    """select on value of aggregated function

    this one looks like ident.binop.value, but the ident is an
    aggregating function, so that the query has to be altered
    differently: not filter, but group_by and having.
    """

    def __init__(self, t: Any) -> None:
        super().__init__(t)
        logger.debug(f"AggregatedExpression::__init__({t})")

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """
        Evaluate the aggregated function query.
        """
        # Get the query and attribute
        stmt, attr = self.operands[0].identifier.evaluate(env)

        # if not isinstance(stmt, AliasedClass):
        #    stmt = stmt.subquery()

        # Resolve the aggregate function
        f = getattr(func, self.operands[0].function)

        # Group by the main table's ID
        main_table = stmt.column_descriptions[0]["type"]
        group_by_column = getattr(main_table, "id", None)
        if not group_by_column:
            raise ValueError("Main table must have an 'id' column to group by.")

        logger.debug(f"Applying aggregate function {f} to attribute {attr}")

        if self.operation is None:
            raise ValueError(f"Unsupported aggregate operation: {f}")

        op = self.operation  # type: Callable[[Any, Any], Any]

        # Create HAVING clause
        def clause(x: Any) -> Any:
            return op(f(attr), x)

        # Apply GROUP BY and HAVING conditions
        stmt = stmt.group_by(group_by_column).having(clause(self.operands[1].express()))

        return stmt, attr  # Ensure both statement and attribute are returned


class BetweenExpressionAction:
    operands: Any

    def __init__(self, t: Any) -> None:
        self.operands = t[0][0::2]  # every second object is an operand

    def __repr__(self) -> str:
        return "(BETWEEN {} {} {})".format(*tuple(self.operands))

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """
        Evaluates the 'BETWEEN' expression, returning the filtered query and attribute.
        """
        # Retrieve the base query and attribute
        stmt, attr = self.operands[0].evaluate(env)

        # Retrieve the low and high range values
        low_value = self.operands[1].express()
        high_value = self.operands[2].express()

        if low_value is None or high_value is None:
            raise ValueError("Operands[1] or Operands[2] returned None for express().")

        logger.debug(
            f"Applying BETWEEN filter on {attr} with range {low_value} to {high_value}"
        )

        # Apply the BETWEEN filter
        stmt = stmt.filter(attr.between(low_value, high_value))

        return stmt, attr

    def needs_join(self, env: Dict[str, Any]) -> List[Any]:
        return [self.operands[0].needs_join(env)]





@runtime_checkable
class NeedsJoinProtocol(Protocol):
    def needs_join(self, env: Dict[str, Any]) -> List[Any]: ...


class UnaryLogical:
    ## abstract base class. `name` is defined in derived classes

    name: str = "UNARY"
    op: Any
    operand: Any

    def __init__(self, t: Any) -> None:
        self.op, self.operand = t[0]

    def __repr__(self) -> str:
        return f"{self.name} {str(self.operand)}"

    def needs_join(self, env: Dict[str, Any]) -> List[Any]:
        """
        Return join steps from operand, ensuring a flat list.
        """
        if isinstance(self.operand, NeedsJoinProtocol):
            return self.operand.needs_join(env)
        return []


class BinaryLogical:
    ## abstract base class. `name` is defined in derived classes
    op: Any
    operands: List[Any]
    name: str  # Explicit declaration needed

    def __init__(self, t: Any) -> None:
        self.op = t[0][1]
        self.operands = t[0][0::2]

    def __repr__(self) -> str:
        return f"({self.operands[0]} {self.name} {self.operands[1]})"

    def needs_join(self, env: Dict[str, Any]) -> List[Any]:
        #        left = self.operands[0].needs_join(env) or []
        #        right = self.operands[1].needs_join(env) or []
        left = self.operands[0].needs_join(env)
        right = self.operands[1].needs_join(env)
        # ✅ Flatten the list and remove unnecessary nesting
        combined = left + right
        return [item for item in combined if item] if combined else [[]]


class SearchAndAction(BinaryLogical):
    name: str = "AND"

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        result, attr = self.operands[0].evaluate(env)
        for operand in self.operands[1:]:
            tmp_result, attr = operand.evaluate(env)
            result = result.intersect(tmp_result)
        return result, attr


#    def evaluate(self, env):
#        """Evaluates AND condition using SQLAlchemy expressions."""
#        stmt, attr = self.operands[0].evaluate(env)
#        conditions = [operand.evaluate(env)[0] for operand in self.operands[1:]]

#        return stmt.where(and_(*[c.scalar_subquery() if isinstance(c, Select) else c for c in conditions]))
# return stmt.where(and_(*conditions)), attr


# class SearchOrAction(BinaryLogical):
#    name = 'OR'

# def evaluate(self, env):
#     result = self.operands[0].evaluate(env)
#     for operand in self.operands[1:]:
#         first_stmt = self.operands[0].evaluate(env)
#         print("First operand stmt:", first_stmt.compile(dialect=env.session.bind.dialect, compile_kwargs={"literal_binds": True}))
#         result = result.union(operand.evaluate(env))
#         union_stmt = result  # after union
#         print("After union, SQL:", select(env.domain).select_from(union_stmt).compile(dialect=env.session.bind.dialect, compile_kwargs={"literal_binds": True}))
#     return result

#    def evaluate(self, env):
#        """Evaluates OR condition using SQLAlchemy expressions."""
#       stmt, attr = self.operands[0].evaluate(env)
#       conditions = [operand.evaluate(env) for operand in self.operands[1:]]

#       return stmt.where(or_(*conditions))
#    def evaluate(self, env):
#        result,attr = self.operands[0].evaluate(env)
#        for i in self.operands[1:]:
#            tmp,attr = i.evaluate(env)
#            result = result.union(tmp)
#        return result


class SearchOrAction(BinaryLogical):
    name: str = "OR"

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """Evaluates OR condition using SQLAlchemy expressions."""
        first_stmt, attr = self.operands[0].evaluate(env)

        # Start with the first operand's query
        combined_stmt = first_stmt

        # Iterate through remaining operands and apply UNION
        for operand in self.operands[1:]:
            operand_stmt, _ = operand.evaluate(env)
            combined_stmt = combined_stmt.union(operand_stmt)

        # ✅ Ensure return type is (stmt, attr)
        return combined_stmt, attr


class SearchNotAction(UnaryLogical):
    name: str = "NOT"

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """
        Evaluate the NOT action, which excludes the results of the operand
        from the base query.
        """

        # Ensure domain resolution
        domain = env["domain"]

        # Select only the primary key
        primary_key_column = inspect(domain).primary_key[0]
        stmt = select(primary_key_column)

        # Exclude the operand's results using an EXCEPT clause
        operand_stmt, attr = self.operand.evaluate(env)

        # Ensure operand_stmt also selects only the primary key
        operand_stmt = operand_stmt.with_only_columns(primary_key_column)

        # Apply the EXCEPT clause to exclude results
        stmt = stmt.except_(operand_stmt)

        return stmt, attr


from typing import Dict, List, Protocol, Tuple

from sqlalchemy.sql.selectable import Select


class Evaluatable(Protocol):
    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]: ...
    def needs_join(self, env: Dict[str, Any]) -> List[Any]: ...


class ParenthesisedQuery:
    content: Evaluatable

    def __init__(self, t: Any) -> None:
        self.content = t[1]

    def __repr__(self) -> str:
        return f"({self.content.__repr__()})"

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        return self.content.evaluate(env)

    def needs_join(self, env: Dict[str, Any]) -> List[Any]:
        return self.content.needs_join(env)


class QueryAction:
    """
    Represents a structured database query action that interacts with a search strategy.

    This class is responsible for:
    - Storing the parsed search query, including its domain and filtering criteria.
    - Validating the domain against the available search domains.
    - Constructing and executing ORM-based database queries using SQLAlchemy.
    - Handling query execution results and ensuring proper filtering.

    Attributes:
        domain (str): The search domain extracted from the parsed query.
                      This typically represents a table or entity class name.
        filter (Expression): The filtering condition extracted from the parsed query.
                             This is expected to be an object that implements
                             `evaluate(self)`, returning a SQLAlchemy query condition.
        search_strategy (MapperSearch or similar object): The search strategy responsible
                                                          for executing the query logic.
        session (Session): The SQLAlchemy session used for executing queries.
        domains (list): List of relationships or tables that need to be joined for
                        executing the query.

    Methods:
        __init__(t):
            Initializes the QueryAction object with a domain and filter expression.

        __repr__():
            Returns a string representation of the query statement.

        invoke(search_strategy):
            Executes the query using the given search strategy and returns results.

    """

    domain: str
    filter: Any
    domains: List[Any]

    def __init__(self, t: Any) -> None:
        """
        QueryAction represents a structured database query.

        :param t: Parsed tokens from pyparsing.
        """
        self.domain = t[0]  # The domain/table name being queried
        self.filter = t[1][0]  # The filtering condition (expression tree)

    def __repr__(self) -> str:
        return f"SELECT * FROM {self.domain} WHERE {self.filter}"

    def invoke(self, search_strategy: Any) -> Set[Any]:
        """
        Executes the parsed query using the given search strategy.
        """
        logger.debug(
            f"QueryAction:invoke - {type(self.domain)}({self.domain}) {type(self.filter)}({self.filter})"
        )

        # Ensure domain resolution
        domain = self.domain
        if domain in search_strategy._shorthand:
            domain = search_strategy._shorthand[domain]

        if domain not in search_strategy._domains:
            raise KeyError(f"Unknown search domain: {domain}")

        domain_class = search_strategy._domains[domain][0]
        session = search_strategy._session

        if not session:
            raise ValueError("Session is required for query execution.")

        # ✅ Create an `env` dictionary to pass correctly formatted data
        env = {
            "domain": domain_class,
            "session": session,
            "search_strategy": search_strategy,  # Ensure `search_strategy` is available
        }

        # Ensure `needs_join` is called before passing to evaluate
        self.domains = self.filter.needs_join(env)

        # ✅ Pass the correct `env` format
        stmt, attr = self.filter.evaluate(env)

        # Debugging: Print the compiled SQL query
        compiled_sql = stmt.compile(
            dialect=session.bind.dialect, compile_kwargs={"literal_binds": True}
        )
        print(f"DEBUG: Compiled SQL Query:\n{compiled_sql}")

        # ✅ Ensure only primary key (`id`) is selected
        inspect(domain_class).primary_key[0]  # Get the primary key column
        # stmt = select(primary_key_column).where(stmt.whereclause)  # Modify query to select only the primary key

        # if isinstance(stmt, CompoundSelect):
        #     # Handle union queries by selecting only primary key from each subquery
        #     subqueries = [select(primary_key_column).select_from(subq.subquery()) for subq in stmt.selects]
        #     final_stmt = union_all(*subqueries)
        # else:
        #     final_stmt = select(primary_key_column).where(stmt.whereclause)

        # # Execute the query
        # result = set(session.execute(final_stmt).scalars().all())

        # Execute the query and retrieve ORM objects
        try:
            result = set(session.scalars(stmt).all())
        except NoResultFound:
            result = set()

        if None in result:
            logger.warning("Removing None from result set")
            result.discard(None)

        return result


from typing import Any, Protocol


class Invokable(Protocol):
    def invoke(self, search_strategy: Any) -> Any: ...


class StatementAction:
    """
    A wrapper class representing a parsed statement in the search query.

    This class is designed to store and process a parsed statement from the query
    and delegate its execution to the appropriate search strategy.

    Attributes:
        content (Any): The parsed statement object extracted from the input list `t`.

    Methods:
        __init__(t):
            Initializes the StatementAction instance with the first element of `t`,
            assuming `t` is a list-like structure containing parsed elements.

        __repr__():
            Returns a string representation of the `content` attribute.

        invoke(search_strategy):
            Delegates execution to the `invoke` method of the `content` attribute,
            using the provided search strategy.

    """

    content: Invokable

    def __init__(self, t: list[Any]) -> None:
        """
        Initializes the StatementAction object with parsed content.

        Args:
            t (list): A list-like structure where the first element (t[0])
                      is expected to be the parsed statement object.

        Raises:
            IndexError: If `t` is empty or does not contain at least one element.
            TypeError: If `t[0]` does not have an `invoke` method (unexpected structure).

        Expected Behavior:
            - The first element of `t` should be a valid parsed statement that can be
              further processed.
            - It is assumed that `t` follows a structure where `t[0]` represents a
              query-related object.

        Example Usage:
            t = [ParsedQueryStatement(...)]
            stmt_action = StatementAction(t)
        """
        if not t or not hasattr(t[0], "invoke"):
            raise TypeError(f"Invalid statement provided: {t}")
        self.content = t[0]

    def __repr__(self) -> str:
        """
        Returns a string representation of the StatementAction instance.

        Returns:
            str: A string representation of the contained content, which is
                 usually a parsed statement.

        Expected Behavior:
            - Should return a human-readable representation of `content`, useful
              for debugging and logging.
            - Assumes that `content` itself has a meaningful `__repr__` method.

        Example Output:
            "<ParsedQueryStatement WHERE genus='genus3'>"
        """
        return repr(self.content)

    def invoke(self, search_strategy: Any) -> Any:
        """
        Executes the parsed statement using the given search strategy.

        Args:
            search_strategy (MapperSearch or similar object):
                The search strategy responsible for executing the query logic.

        Returns:
            Any: The result of invoking the statement's `invoke` method with the
                 provided search strategy. This is typically a set of database
                 identifiers or ORM results.

        Raises:
            AttributeError: If `self.content` does not have an `invoke` method,
                            indicating that `content` is not a properly parsed
                            query statement.

        Expected Behavior:
            - Calls `invoke` on the parsed statement (`self.content`) with the
              provided search strategy.
            - The search strategy determines how the parsed statement is executed,
              typically returning a filtered query result.

        Example Usage:
            stmt_action = StatementAction([ParsedQueryStatement(...)])
            results = stmt_action.invoke(my_search_strategy)
        """
        if not hasattr(self.content, "invoke"):
            raise AttributeError("Statement content does not support invocation.")

        try:
            logger.debug(f"Invoking search strategy with: {self.content}")
            return self.content.invoke(search_strategy)
        except Exception as e:
            logger.error(f"Error executing statement: {e}")
            raise RuntimeError(f"Statement execution failed: {e}")




class BinomialNameAction:
    """created when the parser hits a binomial_name token.

    Searching using binomial names returns one or more species objects.
    """

    genus_epithet: str
    species_epithet: str

    def __init__(self, t: list[str]) -> None:
        """
        Initializes a BinomialNameAction.

        Args:
            t (list): Parsed binomial name tokens, where:
                      - t[0] is the genus epithet.
                      - t[1] is the species epithet.
        """
        if len(t) < 2:
            raise ValueError(
                "BinomialNameAction requires both genus and species epithet."
            )

        self.genus_epithet = t[0]
        self.species_epithet = t[1]

    def __repr__(self) -> str:
        return f"{self.genus_epithet} {self.species_epithet}"

    def invoke(self, search_strategy: Any) -> Set[Any]:
        from bauble.plugins.plants.genus import Genus
        from bauble.plugins.plants.species_model import Species

        logger.debug("BinomialNameAction:invoke")

        # ✅ Ensure a valid session is available
        session = search_strategy._session
        if not isinstance(session, Session):
            raise ValueError(
                "Invalid session provided. Expected an instance of sqlalchemy.orm.Session."
            )

        stmt = (
            select(Species)
            .where(
                or_(
                    Species.sp.startswith(self.species_epithet),
                    and_(
                        self.species_epithet == "sp",
                        getattr(Species, "infrasp1") == "sp",
                    ),
                )
            )
            .join(Genus)
            .where(getattr(Genus.genus, "startswith")(self.genus_epithet))
        )

        result = set(search_strategy._session.scalars(stmt).all())

        logger.warning("removing None from result set")
        result.discard(None)
        return result


class DomainExpressionAction:
    """created when the parser hits a domain_expression token.

    Searching using domain expressions is a little more magical than an
    explicit query. you give a domain, a binary_operator and a value,
    the domain expression will return all object with at least one
    property (as passed to add_meta) matching (according to the binop)
    the value.
    """

    domain: str
    cond: str
    values: Any

    def __init__(self, t: List[Any]) -> None:
        if not t or len(t) < 3:
            raise ValueError(
                "Invalid domain expression: requires domain, condition, and values."
            )
        self.domain = t[0]
        self.cond = t[1]
        self.values = t[2]

    def __repr__(self) -> str:
        return f"{self.domain} {self.cond} {self.values}"

    from sqlalchemy import inspect, or_, select

    # def invoke(self, search_strategy):
    #     logger.debug("DomainExpressionAction:invoke")
    #     # Step 1: Validate domain
    #     if self.domain in search_strategy._shorthand:
    #         self.domain = search_strategy._shorthand[self.domain]
    #     if self.domain not in search_strategy._domains:
    #         raise KeyError(f"Unknown search domain: {self.domain}")
    #     cls, properties = search_strategy._domains[self.domain]
    #     # Step 2: Construct SQLAlchemy Query
    #     stmt = select(cls)
    #     # here is the place where to optionally filter out unrepresented
    #     # domain values. each domain class should define its own 'I have
    #     # accessions' filter. see issue #42
    #     # Step 3: Handle the special case where '*' is used
    #     if self.values == "*":
    #         logger.debug(f"Wildcard search on {cls.__name__}, retrieving all records.")
    #         self.stmt = stmt
    #         return set(search_strategy._session.execute(stmt).scalars().all())
    #     # Step 4: Build the filtering logic
    #     try:
    #         mapper = inspect(cls).mapper  # Use inspect to get mapper
    #     except NoInspectionAvailable:
    #         raise ValueError(f"Cannot inspect class {cls}. Ensure it's mapped.")
    #     inspect(cls)  # Validate cls as a mapped class
    #     # Define condition mapping
    #     condition_map = {
    #         "=": lambda col, val: col == val,
    #         "!=": lambda col, val: col != val,
    #         "<": lambda col, val: col < val,
    #         "<=": lambda col, val: col <= val,
    #         ">": lambda col, val: col > val,
    #         ">=": lambda col, val: col >= val,
    #         "like": lambda col, val: col.like(f"{val}"),
    #         "ilike": lambda col, val: col.ilike(f"{val}"),
    #         "contains": lambda col, val: col.ilike(f"%{val}%"),  # Similar to ilike for flexible search
    #         "has": lambda col, val: col.has(val),  # Used for relationships
    #     }
    #     if self.cond not in condition_map:
    #         raise ValueError(f"Unsupported condition: {self.cond}")
    #     condition_func = condition_map[self.cond]
    #     # Step 5: Apply filters for the properties
    #     filters = []
    #     for col_name in properties:
    #         if not hasattr(cls, col_name):
    #             logger.warning(f"Column '{col_name}' not found on class '{cls}', skipping.")
    #             continue
    #         col = getattr(cls, col_name)
    #         filters.extend([condition_func(col, val) for val in self.values.express()])
    #     if not filters:
    #         raise ValueError("No valid filters could be constructed.")
    #     stmt = stmt.filter(or_(*filters))
    #     self.stmt = stmt
    #     # Step 6: Execute query and return results
    #     results = search_strategy._session.execute(stmt).scalars().all()
    #     result_set = {item for item in results if item is not None}
    #     logger.debug(f"DomainExpressionAction Results: {result_set}")
    #     return result_set

    def invoke(self, search_strategy: Any) -> Set[Any]:
        import operator

        logger.debug("DomainExpressionAction:invoke")

        # ✅ Validate session
        session = search_strategy._session
        if not isinstance(session, Session):
            raise ValueError(
                "Invalid session provided. Expected an instance of sqlalchemy.orm.Session."
            )

        # ✅ Resolve domain name to ORM class
        try:
            if self.domain in search_strategy._shorthand:
                self.domain = search_strategy._shorthand[self.domain]
            cls, properties = search_strategy._domains[self.domain]
        except KeyError:
            raise KeyError(f"Unknown search domain: {self.domain}")

        # ✅ Use `select()` instead of deprecated `query()`
        stmt: Select = select(cls)

        # ✅ Return all records if the value is "*"
        if self.values == "*":
            return set(session.execute(stmt).scalars().all())

        op_map: Dict[str, Callable[[Any, Any], Any]] = {
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }  # exclude "=" since it's handled separately

        if self.cond in ("like", "ilike"):

            def condition(col_name: str) -> Callable[[Any], Any]:
                return lambda val: utils.ilike(getattr(cls, col_name), f"{val}")

        elif self.cond in ("contains", "icontains", "has", "ihas"):

            def condition(col_name: str) -> Callable[[Any], Any]:
                return lambda val: utils.ilike(getattr(cls, col_name), f"%{val}%")

        elif self.cond == "=":

            def condition(col_name: str) -> Callable[[Any], Any]:
                return lambda val: getattr(cls, col_name) == val

        elif self.cond in op_map:

            def condition(col_name: str) -> Callable[[Any], Any]:
                return lambda val: op_map[self.cond](getattr(cls, col_name), val)

        else:
            raise ValueError(f"Unsupported or unsafe operator: {self.cond}")

        filters: List[Any] = []
        for col_name in properties:
            if not hasattr(cls, col_name):
                logger.warning(
                    f"Column '{col_name}' not found on class '{cls}', skipping."
                )
                continue

            #            col = getattr(cls, col_name)
            filters.extend([condition(col_name)(val) for val in self.values.express()])

        # Step 7: Apply OR conditions correctly
        if filters:
            stmt = stmt.where(or_(*filters))

        # Step 8: Execute query
        results = search_strategy._session.execute(stmt).scalars().all()
        result_set: Set[Any] = {item for item in results if item is not None}

        logger.debug(f"DomainExpressionAction Results: {result_set}")
        return result_set


class AggregatingAction:

    function: str
    identifier: Any

    def __init__(self, t: Any) -> None:
        logger.debug(f"AggregatingAction::__init__({t})")
        self.function = t[0]
        self.identifier = t[2]

    def __repr__(self) -> str:
        return f"({self.function} {self.identifier})"

    def needs_join(self, env: Dict[str, Any]) -> List[Any]:
        return [self.identifier.needs_join(env)]

    def evaluate(self, env: Dict[str, Any]) -> Tuple[Select, Any]:
        """return pair (query, attribute)

        let the identifier compute the query and its attribute, we do
        not need alter anything right now since the condition on the
        aggregated identifier is applied in the HAVING and not in the
        WHERE.

        """
        q, a = self.identifier.evaluate(env)
        return q, a


class ValueListAction:

    values: List[ValueABC]

    def __init__(self, t: Any) -> None:
        logger.debug(f"ValueListAction::__init__({t})")
        self.values = t[0]

    def __repr__(self) -> str:
        return str(self.values)

    def express(self) -> List[Any]:
        result = [i.express() for i in self.values]
        print(f"🔍 DEBUG: ValueListAction.express() -> {result} ({type(result)})")
        return result

    from sqlalchemy import or_, select

    def invoke(self, search_strategy: Any) -> Set[Any]:
        """
        Called when the whole search string is a value list.

        Search with a list of values is the broadest search and
        searches all the mapper and the properties configured with
        add_meta().
        """

        logger.debug("ValueListAction:invoke")

        # make searches case-insensitive, in postgres use ilike,
        # in other use upper()
        def ilike_filter(cls: DeclarativeMeta, column: str, value: str) -> Any:
            """Portable case-insensitive filtering."""
            # Use ORM attribute so synonyms/hybrids (e.g., 'epithet') work.
            attr = getattr(cls, column, None)
            if attr is None:
                return None  # skip unknown property instead of crashing
            # Portable case-insensitive match:
            return utils.ilike(attr, f"%{str(value)}%")

        # ✅ Ensure a valid SQLAlchemy session
        session = search_strategy._session
        if not session:
            raise ValueError("A valid session is required for executing searches.")

        result = set()

        for cls, columns in search_strategy._properties.items():
            # Build cross product of columns and values
            column_value_pairs = [
                (column, value) for column in columns for value in self.express()
            ]

            # Build a filter condition for each column-value pair
            filters = []
            for column, value in column_value_pairs:
                pred = ilike_filter(cls, column, value)
                if pred is not None:
                    filters.append(pred)
            if not filters:
                continue

            # Execute the query for the current class
            query = select(cls).where(or_(*filters))

            # Print the compiled SQL query for debugging
            compiled_sql = query.compile(
                dialect=session.bind.dialect, compile_kwargs={"literal_binds": True}
            )
            print(f"DEBUG: Generated SQL Query: {compiled_sql}")

            query_result = search_strategy._session.scalars(query).all()
            print(f"→ {cls.__name__}: {len(query_result)} hits")
            if query_result:
                # show a peek of identity keys
                try:
                    from sqlalchemy import inspect as _insp
                    print("   ids:", [getattr(o, _insp(o).mapper.primary_key[0].key) for o in query_result[:5]])
                except Exception:
                    pass
            result.update(query_result)

        # Post-process the results
        def replace(item: Any) -> Any:
            try:
                replacement = item.replacement()
                logger.debug("Replacing %s with %s in result set", item, replacement)
                return replacement or item
            except Exception as e:
                logger.debug("No replacement for %s due to: %s", item, e)
                return item

        result = {replace(item) for item in result if item is not None}

        logger.debug("Result is now %s", result)
        return result


wordStart, wordEnd = WordStart(), WordEnd()


class SearchParser:
    """The parser for bauble.search.MapperSearch"""

    def debug_parse_action(
        self, name: str
    ) -> Callable[[str, int, ParseResults], ParseResults]:
        """Returns a parse action that prints the parsed tokens with a label."""

        def action(s: str, loc: int, tokens: ParseResults) -> Any:
            print(
                f"🔍 {name} parsed:", tokens.dump()
            )  # Print structured result with a label
            return tokens  # Ensure the original tokens are returned

        return action

    def __init__(self) -> None:
        numeric_value = Regex(r"[-]?\d+(\.\d*)?([eE]\d+)?").set_parse_action(
            NumericToken
        )("number")
        unquoted_string = Word(alphanums + alphas8bit + "%.-_*;:")
        string_value = (
            (quotedString.set_parse_action(removeQuotes) | unquoted_string)
            .set_parse_action(self.debug_parse_action("string_value"))
            .set_parse_action(StringToken)("string")
        )

        none_token = (
            Literal("None")
            .set_parse_action(self.debug_parse_action("none_token"))
            .set_parse_action(NoneToken)
        )
        empty_token = (
            Literal("Empty")
            .set_parse_action(self.debug_parse_action("empty_token"))
            .set_parse_action(EmptyToken)
        )

        self.value_list: Forward = Forward()
        typed_value = (
            (
                Literal("|")
                + unquoted_string
                + Literal("|")
                + self.value_list
                + Literal("|")
            )
            .set_parse_action(self.debug_parse_action("typed_value"))
            .set_parse_action(TypedValueToken)
        )

        AND_ = wordStart + (CaselessLiteral("AND") | Literal("&&")) + wordEnd
        OR_ = wordStart + (CaselessLiteral("OR") | Literal("||")) + wordEnd
        NOT_ = wordStart + (CaselessLiteral("NOT") | Literal("!")) + wordEnd
        BETWEEN_ = wordStart + CaselessLiteral("BETWEEN") + wordEnd

        value = (
            (
                typed_value
                | WordStart("0123456789.-e") + numeric_value + WordEnd("0123456789.-e")
                | none_token
                | empty_token
                | string_value
            )
            .set_parse_action(self.debug_parse_action("value"))
            .set_parse_action(ValueToken)("value")
        )
        self.value_list <<= (
            Group(OneOrMore(value) ^ DelimitedList(value))
            .set_parse_action(self.debug_parse_action("value_list"))
            .set_parse_action(ValueListAction)("value_list")
        )

        domain = Word(alphas, alphanums)

        # binop = MatchFirst([Literal("is not"), Literal("="), Literal("=="), Literal("!="), Literal("<>"), Literal("<"), Literal("<="), Literal(">="), Literal("not"), Literal("like"), Literal("contains"), Literal("has"), Literal("ilike"), Literal("icontains"), Literal("ihas"), Literal("is")])
        binop = one_of(
            "= == != <> < <= > >= not like contains has ilike icontains ihas is"
        ).set_parse_action(self.debug_parse_action("binop"))
        binop = MatchFirst(
            [
                CaselessKeyword("is not"),
                one_of(
                    "= == != <> < <= > >= not like contains has ilike icontains ihas is"
                ),
            ]
        )
        binop_set = one_of("in")
        equals = Literal("=")
        star_value = Literal("*")
        domain_values = (self.value_list.copy())("domain_values")
        domain_expression = (
            (domain + equals + star_value + stringEnd)
            | (domain + binop + domain_values + stringEnd)
        ).set_parse_action(lambda t: DomainExpressionAction(t))("domain_expression")

        caps = srange("[A-Z]")
        lowers = caps.lower()
        binomial_name = (Word(caps, lowers) + Word(lowers)).set_parse_action(
            lambda t: BinomialNameAction(t)
        )("binomial_name")

        aggregating_func = (
            Literal("sum") | Literal("min") | Literal("max") | Literal("count")
        )

        query_expression = Forward()
        query_expression.set_name("filter")

        atomic_identifier = Word(alphas + "_", alphanums + "_")
        identifier = Group(
            atomic_identifier
            + ZeroOrMore("." + atomic_identifier)
            + "["
            + atomic_identifier
            + binop
            + value
            + "]"
            + "."
            + atomic_identifier
        ).setParseAction(FilteredIdentifierAction) | Group(
            atomic_identifier + ZeroOrMore("." + atomic_identifier)
        ).setParseAction(
            IdentifierAction
        )
        aggregated = (
            aggregating_func + Literal("(") + identifier + Literal(")")
        ).set_parse_action(AggregatingAction)
        ident_expression = (
            Group(identifier + binop + value).set_parse_action(IdentExpression)
            | Group(identifier + binop_set + self.value_list).set_parse_action(
                ElementSetExpression
            )
            | Group(aggregated + binop + value).set_parse_action(AggregatedExpression)
            | (Literal("(") + query_expression + Literal(")")).set_parse_action(
                ParenthesisedQuery
            )
        ).set_parse_action(self.debug_parse_action("ident_expression"))
        between_expression = Group(
            identifier + BETWEEN_ + value + AND_ + value
        ).set_parse_action(BetweenExpressionAction)
        query_expression <<= (
            infix_notation(
                (ident_expression | between_expression),
                [
                    (NOT_, 1, OpAssoc.RIGHT, SearchNotAction),
                    (AND_, 2, OpAssoc.LEFT, SearchAndAction),
                    (OR_, 2, OpAssoc.LEFT, SearchOrAction),
                ],
            )
            .set_debug(True, False)
            .set_parse_action(self.debug_parse_action("query_expression"))
        )
        query = (
            (
                domain
                + Keyword("where", caseless=True).suppress()
                + Group(query_expression)
                + stringEnd
            )
            .set_parse_action(self.debug_parse_action("query"))
            .set_parse_action(QueryAction)
        )

        self.statement = (
            query("query")
            | domain_expression("domain")
            | binomial_name("binomial")
            | self.value_list("value_list")
        ).set_parse_action(lambda t: StatementAction(t))("statement")

    def parse_string(self, text: str) -> Any:
        """request pyparsing object to parse text

        `text` can be either a query, or a domain expression, or a list of
        values. the `self.statement` pyparsing object parses the input text
        and return a pyparsing.ParseResults object that represents the input
        """

        result = self.statement.parse_string(text)

        # ✅ Debugging Step: Print the raw parse result
        print("🔍 PARSE RESULT:", result.dump())
        return result


class SearchStrategy:
    """
    Interface for adding search strategies to a view.
    """

    def search(self, text: str, session: Optional[Session] = None, **kwargs,) -> Set[Any]:
        """
        :param text: the search string
        :param session: the session to use for the search

        Return an iterator that iterates over mapped classes retrieved
        from the search.
        """
        logger.debug(f'SearchStrategy "{text}"({self.__class__.__name__})')
        return set()


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

    _results: Set[Any]
    parser: Any
    _session: Optional[Session]
    _domains: Dict[str, Tuple[Any, List[str]]] = {}
    _shorthand: Dict[str, str] = {}
    _properties: Dict[Any, List[str]] = {}

    def __init__(self) -> None:
        super().__init__()
        self._results = set()
        self.parser = SearchParser()

    def add_meta(
        self,
        domain: Union[str, List[str], Tuple[str, ...]],
        cls: Any,
        properties: List[str],
    ) -> None:
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

        logger.debug(f"{self}.add_meta({domain}, {cls}, {properties})")

        check(
            isinstance(properties, list),
            _("MapperSearch.add_meta(): " "default_columns argument must be list"),
        )
        check(
            len(properties) > 0,
            _("MapperSearch.add_meta(): " "default_columns argument cannot be empty"),
        )
        if isinstance(domain, (list, tuple)):
            self._domains[domain[0]] = (cls, properties)
            for d in domain[1:]:
                self._shorthand[d] = domain[0]
        else:
            # Extract the first word for single-word domain strings
            # domain_key = domain.split(" ")[0]
            self._domains[domain] = (cls, properties)
        self._properties[cls] = properties

    @classmethod
    def get_domain_classes(cls) -> Dict[str, Any]:

        d: Dict[str, Any] = {}
        for domain, item in cls._domains.items():
            d.setdefault(domain, item[0])
        return d

    def search(self, text: str, session: Optional[Session] = None, **kwargs) -> Set[Any]:
        """
        Perform a text-based search on the database using the MapperSearch strategy.

        Args:
            text (str): The query string specifying the search criteria.
                        This should be a valid expression that can be parsed by the internal parser.
                        Example formats:
                        - "genus where genus=genus3 AND family.family=fam3"
                        - "plant where accession.species.genus.family.family='Orchidaceae' AND accession.species.genus.family.qualifier=''"
            session (Session, optional): The SQLAlchemy session object to use for the query.
                                         If None, a session should be explicitly closed after use to prevent database deadlocks.

        Returns:
            set: A set of ORM objects matching the search criteria. If no matches are found, an empty set is returned.

        Raises:
            Exception: If the query parsing fails or if there are issues executing the SQL queries.
        """

        # ✅ Ensure a valid session is provided
        if session is None:
            raise ValueError("Session must be provided for searching.")

        self._session = session  # ✅ Store session properly for queries

        super().search(text, session)
        # self._session = session  # Store the session for use in querying

        # Clear any previous search results
        self._results.clear()

        # Step 1: Parse the input search string
        parse_result = self.parser.parse_string(
            text
        )  # Convert search text into an actionable statement
        statement = parse_result.statement  # Extract the parsed statement object
        logger.debug(f"statement : {type(statement)}({statement})")
        print(
            f"DEBUG: MapperSearch.search() - Parsed statement type: {type(statement)}"
        )

        # Step 2: Ensure `invoke()` returns a valid statement
        # select_stmt, attr = statement.invoke(self)
        # Invoke the parsed statement and retrieve raw results (likely a set of IDs or objects)
        raw_results = statement.invoke(self)
        logger.debug(f"raw_results : {raw_results}")

        # ✅ Ensure raw_results is a fresh set to prevent shared state issues
        if raw_results:
            raw_results = set(
                raw_results
            )  # Create a new set to avoid modifying shared references

        # Extract the action name, which determines how the query should be processed
        action_name = (
            parse_result.getName()
        )  # Possible values: "domain_expression", "query", "value_list"
        logger.debug("Pyparsing action: %s", action_name)
        logger.debug("raw_results = %s", raw_results)

        # If no results were found, return an empty set immediately
        if not raw_results:
            return set(self._results)  # Return an empty result set

        # Step 3: Check if raw_results contains primary keys instead of full objects
        first_result = (
            next(iter(raw_results)) if raw_results else None
        )  # Get first result
        if isinstance(first_result, int):  # ✅ Assume raw_results are primary keys
            domain_name = text.split(" ")[0]  # Extract domain name from query
            domain_class = self._domains.get(domain_name, [None])[0]

            if domain_class:
                # ✅ Fetch full ORM objects
                stmt = select(domain_class).where(domain_class.id.in_(raw_results))

                # ✅ Print raw SQL for debugging
                compiled_sql = stmt.compile(
                    self._session.bind, compile_kwargs={"literal_binds": True}
                )
                print("\n🔍 GENERATED SQL:\n", compiled_sql)

                full_results = set(self._session.execute(stmt).scalars().all())
                self._results.update(full_results)
            else:
                self._results.update(raw_results)  # Fallback to raw results
        else:
            self._results.update(raw_results)

        # Return the final set of search results
        return set(self._results)


# list of search strategies to be tried on each search string
_search_strategies: Dict[str, SearchStrategy] = {"MapperSearch": MapperSearch()}


def add_strategy(strategy: Callable[[], SearchStrategy]) -> None:
    obj = strategy()
    _search_strategies[obj.__class__.__name__] = obj


def get_strategy(name: str) -> Optional[SearchStrategy]:
    strategy = _search_strategies.get(name)
    return strategy


# def get_strategy(name):
#    return _search_strategies.get(name, None)


class SchemaBrowser:
    """
    A UI component for browsing schema properties.
    """

    container: Any
    domain_map: Dict[str, Any]
    table_combo: Any
    prop_tree: Any

    def __init__(self) -> None:
        self.container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # WARNING: this is a hack from MapperSearch
        self.domain_map = MapperSearch.get_domain_classes().copy()

        # Search Domain Selection
        frame = Gtk.Frame(label=_("Search Domain"))
        self.container.pack_start(frame, False, False, 0)

        self.table_combo = Gtk.ComboBoxText()
        frame.add(self.table_combo)
        for key in sorted(self.domain_map.keys()):
            self.table_combo.append_text(key)

        self.table_combo.connect("changed", self.on_table_combo_changed)

        # Property TreeView
        self.prop_tree = Gtk.TreeView()
        self.prop_tree.set_headers_visible(False)

        cell = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Property"), cell)
        self.prop_tree.append_column(column)
        column.add_attribute(cell, "text", 0)

        self.prop_tree.connect("test_expand_row", self.on_row_expanded)

        # Domain Properties Frame
        frame = Gtk.Frame(label=_("Domain Properties"))
        sw = Gtk.ScrolledWindow()
        sw.add(self.prop_tree)
        frame.add(sw)
        self.container.pack_start(frame, True, True, 0)

    def _insert_props(
        self, mapper: Any, model: Gtk.TreeStore, treeiter: Gtk.TreeIter
    ) -> None:
        """
        Insert the properties from mapper into the model at treeiter
        """
        column_properties = sorted(
            [
                x
                for x in mapper.iterate_properties
                if isinstance(x, ColumnProperty) and not x.key.startswith("_")
            ],
            key=lambda k: (k.key != "id", not k.key.endswith("_id"), k.key),
        )
        for prop in column_properties:
            model.append(treeiter, [prop.key, prop])

        relation_properties = sorted(
            [
                x
                for x in mapper.iterate_properties
                if isinstance(x, RelationProperty) and not x.key.startswith("_")
            ],
            key=lambda k: k.key,
        )
        for prop in relation_properties:
            it = model.append(treeiter, [prop.key, prop])
            model.append(it, ["", None])

    def on_row_expanded(
        self, treeview: Gtk.TreeView, treeiter: Gtk.TreeIter, path: Gtk.TreePath
    ) -> None:
        """
        Called before the row is expanded and populates the children of the
        row.
        """
        logger.debug("on_row_expanded")
        model = treeview.props.model
        parent = treeiter
        while model.iter_has_child(treeiter):
            nkids = model.iter_n_children(parent)
            child = model.iter_nth_child(parent, nkids - 1)
            model.remove(child)

        # prop should always be a RelationProperty
        prop = treeview.props.model[treeiter][1]
        self._insert_props(prop.mapper, model, treeiter)

    def on_table_combo_changed(self, combo: Gtk.ComboBoxText, *args: Any) -> None:
        """
        Change the table to use for the query
        """
        utils.clear_model(self.prop_tree)
        it = combo.get_active_iter()
        domain = combo.props.model[it][0]
        mapper = inspect(self.domain_map[domain])
        model = Gtk.TreeStore(str, object)
        root = model.get_iter_root()
        self._insert_props(mapper, model, root)
        self.prop_tree.set_property("model", model)
