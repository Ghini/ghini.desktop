#
# species.py
#

from species_editor import *
from species_model import *
from bauble.view import SearchView, SearchStrategy, MapperSearch

__all__ = ['species_table', 'Species', 'species_synonym_table',
           'SpeciesSynonym', 'vernacular_name_table', 'VernacularName',
           'species_context_menu', 'species_markup_func', 'vernname_get_kids',
           'vernname_markup_func', 'vernname_context_menu', 'SpeciesEditor',
           'SpeciesInfoBox', 'VernacularNameInfoBox',
           'species_distribution_table', 'SpeciesDistribution']#, 'SpeciesSearch']


## class SpeciesSearch(MapperSearch):

##     def __init__(self):
##         super(SpeciesSearch, self).__init__(Species, ['sp', 'infrasp'])

##     def search(self, tokens, session):
##         results = super(SpeciesSearch, self).search(tokens, session)
##         #if 'values' in tokens:
##         #    print str(tokens)
##         #else if 'expression

##         return results
