import os
import sys

from sqlalchemy import *
from sqlalchemy.exc import *

# TURN OFF desktop.open for this module so that the test doesn't open
# the report
import bauble.utils.desktop as desktop
desktop.open = lambda x: x

from bauble.test import BaubleTestCase
import bauble.utils as utils
from bauble.utils.log import debug
#import bauble.plugins.report as report_plugin
from bauble.plugins.report import get_all_species, get_all_accessions, \
     get_all_plants
from bauble.plugins.plants import Family, Genus, Species, \
    SpeciesDistribution, VernacularName, Geography
from bauble.plugins.garden import Accession, Plant, Location
from bauble.plugins.tag import tag_objects, Tag
from bauble.plugins.report.template import TemplateFormatterPlugin


class TemplateFormatterTests(BaubleTestCase):

    def __init__(self, *args):
        super(TemplateFormatterTests, self).__init__(*args)

    def setUp(self, *args):
        super(TemplateFormatterTests, self).setUp()
        fctr = gctr = sctr = actr = pctr = 0
        for f in xrange(2):
            fctr+=1
            family = Family(id=fctr, family=u'fam%s' % fctr)
            self.session.add(family)
            for g in range(2):
                gctr+=1
                genus = Genus(id=gctr, family=family, genus=u'gen%s' % gctr)
                self.session.add(genus)
                for s in range(2):
                    sctr+=1
                    sp = Species(id=sctr, genus=genus, sp=u'sp%s' % sctr)
                    # TODO: why doesn't this geography, species
                    # distribution stuff seem to work
                    geo = Geography(id=sctr, name=u'Mexico%s' % sctr)
                    dist = SpeciesDistribution(geography_id=sctr)
                    sp.distribution.append(dist)
                    vn = VernacularName(id=sctr, species=sp,
                                        name=u'name%s' % sctr)
                    self.session.add_all([sp, geo, dist, vn])
                    for a in range(2):
                        actr+=1
                        acc = Accession(id=actr, species=sp, code=u'%s' % actr)
                        self.session.add(acc)
                        for p in range(2):
                            pctr+=1
                            loc = Location(id=pctr, site=u'site%s' % pctr)
                            plant = Plant(id=pctr, accession=acc, location=loc,
                                          code=u'%s' % pctr)
                            #debug('fctr: %s, gctr: %s, actr: %s, pctr: %s' \
                            #      % (fctr, gctr, actr, pctr))
                            self.session.add_all([loc, plant])
        self.session.commit()

    def tearDown(self, *args):
        super(TemplateFormatterTests, self).tearDown(*args)

    def test_format(self):
        plants = self.session.query(Plant).all()
        filename = os.path.join(os.path.dirname(__file__), 'labels.html')
        report = TemplateFormatterPlugin.format(plants, template=filename)
        open('/tmp/testlabels.html', 'w').write(report)
        #print >>sys.stderr, report
        # TODO: need to make some sort of assertion here


