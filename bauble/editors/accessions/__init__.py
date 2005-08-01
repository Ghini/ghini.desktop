#
# Plantnames editor module
#

from tables import tables
from editors import editors
import accessions
editors.register(accessions.AccessionsEditor, tables.Accessions)