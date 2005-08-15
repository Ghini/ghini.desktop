from bauble.plugins import BaublePlugin

from country import Country

class GeographyPlugin(BaublePlugin):
    #editors = []
    tables = [Country]
    #views = []
    #depends = []

plugin = GeographyPlugin