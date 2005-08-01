#
# Images editor module
#

from tables import tables
from editors import editors
import images
editors.register(images.ImagesEditor, tables.Images)