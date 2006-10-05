# util.sql
#
# Description: sql utility functions

from sqlalchemy import *

def count_distinct_whereclause(table_column, whereclause):
    return select([table_column], whereclause, distinct=True).alias('dummy').count().scalar()

def count(table, where_clause=None):                    
    s = select([func.count('*')], from_obj=[table])
    if where_clause is not None:
        s.append_whereclause(where_clause)
    return s.scalar()

def count_select(sel):
    return sel.alias('sdasdasd').count().scalar()