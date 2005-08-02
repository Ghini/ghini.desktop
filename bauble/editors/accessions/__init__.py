#
# Plantnames editor module
#

from tables import tables
import editors
import accessions
editors.editors.register(accessions.AccessionsEditor, tables.Accessions)