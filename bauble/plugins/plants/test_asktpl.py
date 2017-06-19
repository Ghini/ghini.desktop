# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
#
# Description: test for the Plant plugin
#

from bauble.test import BaubleTestCase
import requests

def requests_get(x, timeout=None):
    answers = {'http://www.theplantlist.org/tpl1.1/search?q=Mangifera indica&csv=true': 'ID,Major group,Family,Genus hybrid marker,Genus,Species hybrid marker,Species,Infraspecific rank,Infraspecific epithet,Authorship,Taxonomic status in TPL,Nomenclatural status from original data source,Confidence level,Source,Source id,IPNI id,Publication,Collation,Page,Date,Accepted ID\nkew-2362842,A,Anacardiaceae,,Mangifera,,"indica",,"","L.",Accepted,,M,WCSP (in review),,69913-1,"Sp. Pl.","200","","1753",\n',
               'http://www.theplantlist.org/tpl1.1/search?q=Iris florentina&csv=true': 'ID,Major group,Family,Genus hybrid marker,Genus,Species hybrid marker,Species,Infraspecific rank,Infraspecific epithet,Authorship,Taxonomic status in TPL,Nomenclatural status from original data source,Confidence level,Source,Source id,IPNI id,Publication,Collation,Page,Date,Accepted ID\nkew-321828,A,Iridaceae,,Iris,×,"florentina",,"","L.",Synonym,,H,iPlants,321828,438598-1,"Syst. Nat. ed. 10","2: 863","","1759",kew-321867\ntro-16602596,A,Iridaceae,,Iris,,"florentina",,"","L.",Unresolved,,L,TRO,16602596,,"Syst. Nat. (ed. 10)","863","863","",\nkew-329134,A,Iridaceae,,Iris,×,"florentina",var.,"albicans","(Lange) Baker",Synonym,,L,iPlants,329134,,"J. Linn. Soc., Bot.","16: 146","","1877",kew-321543\nkew-350225,A,Iridaceae,,Iris,×,"florentina",subsp.,"albicans","(Lange) K.Richt.",Synonym,,L,iPlants,350225,,"Pl. Eur.","1: 255","","1890",kew-321543\nkew-329155,A,Iridaceae,,Iris,×,"florentina",var.,"illyrica","(Tomm. ex Vis.) Fiori",Synonym,,L,iPlants,329155,,"Nuov. Fl. Italia","1: 299","","1923",kew-329154\nkew-329192,A,Iridaceae,,Iris,×,"florentina",var.,"madonna","(Dykes) L.H.Bailey",Synonym,,L,iPlants,329192,,"Cycl. Amer. Hort.","2: 1672","","1933",kew-321543\nkew-341075,A,Iridaceae,,Iris,×,"florentina",var.,"pallida","Nyman",Synonym,,L,iPlants,341075,,"Consp. Fl. Eur.","700","","1882",kew-321867\n',
               'http://www.theplantlist.org/tpl1.1/search?q=kew-321867&csv=true': 'ID,Major group,Family,Genus hybrid marker,Genus,Species hybrid marker,Species,Infraspecific rank,Infraspecific epithet,Authorship,Taxonomic status in TPL,Nomenclatural status from original data source,Confidence level,Source,Source id,IPNI id,Publication,Collation,Page,Date,Accepted ID\nkew-321867,A,Iridaceae,,Iris,×,"germanica",,"","L.",Accepted,,H,iPlants,321867,438637-1,"Sp. Pl.","38","","1753",\n'
    }
    result = type('FooBar', (object,), {})()
    result.text = answers.get(x, "")
    print x
    return result

requests.get = requests_get

from ask_tpl import AskTPL, what_to_do_with_it

class TestOne(BaubleTestCase):

    def test_simple_answer(self):
        binomial = 'Mangifera indica'
        AskTPL(binomial, what_to_do_with_it, timeout=2).run()
        infolog = self.handler.messages['bauble.plugins.plants.ask_tpl']['info']
        self.assertEquals(len(infolog), 1)
        self.assertEquals(infolog[0], 'Mangifera indica L. (Anacardiaceae)')

    def test_taxon_is_synonym(self):
        binomial = 'Iris florentina'
        AskTPL(binomial, what_to_do_with_it, timeout=2).run()
        infolog = self.handler.messages['bauble.plugins.plants.ask_tpl']['info']
        self.assertEquals(len(infolog), 2)
        self.assertEquals(infolog[0], 'Iris \xc3\x97florentina L. (Iridaceae)')
        self.assertEquals(infolog[1], 'Iris \xc3\x97germanica L. (Iridaceae) - is its accepted form')
