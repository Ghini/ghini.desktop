#
# Images editor module
#

label = 'Images'
description = 'Images'
depends = ("tables.Images") # tables.Images the module not the table

import images
editor = images.ImagesEditor