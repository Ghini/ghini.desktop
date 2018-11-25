# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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

from . import Taxon, Rank
from bauble.test import BaubleTestCase


def initialize_ranks_and_taxa(self):
    ranks = [
        ('regnum', '', 0, '.name sp.', 'regnum'),
        ('ordo', 'Ordo', 8, '.name sp.', 'ordo'),
        ('familia', 'Fam.', 10, '.name sp.', 'familia'),
        ('subfamilia', 'Subfam.', 14, '.name sp.', 'subfamilia'),
        ('tribus', 'Tr.', 16, '.name sp.', ''),
        ('subtribus', 'Subtr.', 18, '.name sp.', ''),
        ('genus', 'Gen.', 20, '.name sp.', 'genus'),
        ('subgenus', 'subg.', 25, '.genus subg. .name sp.', ''),
        ('sectio', 'sec.', 30, '.genus sec. .name sp.', ''),
        ('subsectio', 'subsec.', 35, '.genus subsec. .name sp.', ''),
        ('species', 'sp.', 40, '.ranked_name .name', 'binomial'),
        ('subspecies', 'subsp.', 45, '.binomial subsp. .name', ''),
        ('varietas', 'var.', 50, '.binomial var. .name', ''),
        ('forma', 'f.', 55, '.binomial f. .name', ''),
        ('cultivar', 'cv', 99, ".complete '.name'", ''), ]
    for name, short, depth, shows_as, defines in ranks:
        p = Rank(name=name, short=short, depth=depth, shows_as=shows_as, defines=defines)
        self.session.add(p)
    self.session.commit()
    (self.regnum, self.ordo, self.familia, self.subfamilia, self.tribus,
     self.subtribus, self.genus, self.subgenus, self.sectio, self.subsectio,
     self.species, self.subspecies, self.varietas, self.forma, self.cultivar
    ) = self.session.query(Rank).order_by(Rank.depth).all()
    # rank, id, epithet, parent_id, accepted_id
    taxa = [
        (self.regnum, 0, 'Plantae', 0, None), 
        (self.ordo, 1, 'Malvales', 0, None), 
        (self.familia, 2, 'Malvaceae', 1, None),
        (self.subfamilia, 3, 'Sterculioideae', 2, None), 
        (self.subfamilia, 4, 'Tilioideae', 2, None),
        (self.familia, 5, 'Sterculiaceae', 1, 3), 
        (self.familia, 6, 'Tiliaceae', 1, 4), 
        (self.ordo, 7, 'Asparagales', 0, None), 
        (self.familia, 8, 'Orchidaceae', 7, None), 
        (self.subfamilia, 9, 'Vanilloideae', 8, None), 
        (self.subfamilia, 10, 'Orchidoideae', 8, None), 
        (self.subfamilia, 11, 'Epidendroideae', 8, None), 
        (self.genus, 12, 'Magnoliales', 0, None), 
        (self.genus, 13, 'Annonaceae', 12, None), 
        (self.genus, 14, 'Annona', 13, None), 
        (self.genus, 15, 'Xylopia', 13, None), ]
    for rank, id, epithet, parent_id, accepted_id in taxa:
        p = Taxon(rank=rank, id=id, epithet=epithet, parent_id=parent_id, accepted_id=accepted_id)
        self.session.add(p)
    self.session.commit()
    self.plantae = self.session.query(Taxon).filter_by(rank=self.regnum).first()


class CreateRanks(BaubleTestCase):
    def test_can_create_a_rank(self):
        p = Rank(name='Ordo', depth=8, shows_as='.name sp', defines='ordo')
        self.session.add(p)
        self.session.commit()

        q = self.session.query(Rank).all()
        self.assertEquals(len(q), 1)
        self.assertEquals(q[0], p)

    def test_can_create_rank_structure(self):
        ranks = [
            ('ordo', 8, '.name sp.', 'ordo'),
            ('familia', 10, '.name sp.', 'familia'),
            ('subfamilia', 14, '.name sp.', 'subfamilia'),
            ('tribus', 16, '.name sp.', ''),
            ('subtribus', 18, '.name sp.', ''),
            ('genus', 20, '.name sp.', 'genus'),
            ('subgenus', 25, '.genus subg. .name sp.', ''),
            ('sectio', 30, '.genus sec. .name sp.', ''),
            ('subsectio', 35, '.genus subsec. .name sp.', ''),
            ('species', 40, '.ranked_name .name', 'binomial'),
            ('subspecies', 45, '.binomial subsp. .name', ''),
            ('varietas', 50, '.binomial var. .name', ''),
            ('forma', 55, '.binomial f. .name', ''), ]
        for name, depth, shows_as, defines in ranks:
            p = Rank(name=name, depth=depth, shows_as=shows_as, defines=defines)
            self.session.add(p)
        self.session.commit()

        q = self.session.query(Rank).all()
        self.assertEquals(len(q), len(ranks))


class CreateTaxa(BaubleTestCase):
    def setUp(self):
        super().setUp()
        initialize_ranks_and_taxa(self)

    def test_can_follow_accepted_links(self):
        tiliaceae = self.session.query(Taxon).filter_by(id=6).first()
        tilioideae = self.session.query(Taxon).filter_by(epithet='Tilioideae').first()
        self.assertEquals(tiliaceae.epithet, 'Tiliaceae')
        self.assertEquals(tiliaceae.accepted_id, tilioideae.id)
        self.assertEquals(tiliaceae.accepted.epithet, 'Tilioideae')

    def test_can_follow_parent_links(self):
        tiliaceae = self.session.query(Taxon).filter_by(id=6).first()
        malvales = self.session.query(Taxon).filter_by(epithet='Malvales').first()
        self.assertEquals(tiliaceae.epithet, 'Tiliaceae')
        self.assertEquals(tiliaceae.parent_id, malvales.id)
        self.assertEquals(tiliaceae.parent.epithet, 'Malvales')
        

class TestingRepresentation(BaubleTestCase):
    def setUp(self):
        super().setUp()
        initialize_ranks_and_taxa(self)
        
    def test0_creation(self):
        self.assertEquals(self.genus.name, 'genus')
        self.assertEquals(self.plantae.epithet, 'Plantae')
        annona = self.session.query(Taxon).filter_by(id=14).first()
        self.assertEquals(annona.epithet, 'Annona')

    def test1_shows_as_genus_or_above(self):
        tax = self.session.query(Taxon).filter_by(epithet='Annona').first()
        self.assertEquals(tax.show(), 'Annona sp.')
        tax = self.session.query(Taxon).filter_by(epithet='Tilioideae').first()
        self.assertEquals(tax.show(), 'Tilioideae sp.')
        tax = self.session.query(Taxon).filter_by(epithet='Tiliaceae').first()
        self.assertEquals(tax.show(), 'Tiliaceae sp.')
        
    def test2_shows_as_species(self):
        annona = self.session.query(Taxon).filter_by(epithet='Annona').first()
        guanabana = Taxon(rank=self.species, parent=annona, epithet='muricata')
        self.session.add(guanabana)
        self.assertEquals(guanabana.show(), 'Annona muricata')

    def test3_shows_as_subspecies(self):
        cucurbitales = Taxon(rank=self.ordo, parent=self.plantae, epithet='Cucurbitales')
        cucurbitaceae = Taxon(rank=self.familia, parent=cucurbitales, epithet='Cucurbitaceae')
        cucurbita = Taxon(rank=self.genus, parent=cucurbitaceae, epithet='Cucurbita')
        pepo = Taxon(rank=self.species, parent=cucurbita, epithet='pepo')
        cylindrica = Taxon(rank=self.varietas, parent=pepo, epithet='cylindrica')
        self.session.add_all([cucurbitales, cucurbitaceae, cucurbita, pepo, cylindrica])
        self.assertEquals(cylindrica.show(), 'Cucurbita pepo var. cylindrica')
        
    def test4_shows_cultivar(self):
        cucurbitales = Taxon(rank=self.ordo, parent=self.plantae, epithet='Cucurbitales')
        cucurbitaceae = Taxon(rank=self.familia, parent=cucurbitales, epithet='Cucurbitaceae')
        cucurbita = Taxon(rank=self.genus, parent=cucurbitaceae, epithet='Cucurbita')
        pepo = Taxon(rank=self.species, parent=cucurbita, epithet='pepo')
        cylindrica = Taxon(rank=self.varietas, parent=pepo, epithet='cylindrica')
        self.session.add_all([cucurbitales, cucurbitaceae, cucurbita, pepo, cylindrica])

        cv = Taxon(rank=self.cultivar, parent=cylindrica, epithet='Lekker Bek')
        self.assertEquals(cv.show(), "Cucurbita pepo var. cylindrica 'Lekker Bek'")
        cv = Taxon(rank=self.cultivar, parent=pepo, epithet='Lekker Bek')
        self.assertEquals(cv.show(), "Cucurbita pepo 'Lekker Bek'")
        cv = Taxon(rank=self.cultivar, parent=cucurbita, epithet='Lekker Bek')
        self.assertEquals(cv.show(), "Cucurbita sp. 'Lekker Bek'")
        cv = Taxon(rank=self.cultivar, parent=self.plantae, epithet='Lekker Bek')
        self.assertEquals(cv.show(), "Plantae sp. 'Lekker Bek'")

    def test5_shows_speciem_novam(self):
        cucurbitales = Taxon(rank=self.ordo, parent=self.plantae, epithet='Cucurbitales')
        cucurbitaceae = Taxon(rank=self.familia, parent=cucurbitales, epithet='Cucurbitaceae')
        cucurbita = Taxon(rank=self.genus, parent=cucurbitaceae, epithet='Cucurbita')
        sp_nov = Taxon(rank=self.species, parent=cucurbita, nov_code='IGC1033')
        self.assertEquals(sp_nov.show(), 'Cucurbita sp. (IGC1033)')
        sp_nov = Taxon(rank=self.species, parent=cucurbitaceae, nov_code='IGC1034')
        self.assertEquals(sp_nov.show(), 'Cucurbitaceae sp. (IGC1034)')
        cv = Taxon(rank=self.cultivar, parent=sp_nov, epithet='Lekker Bek')
        self.assertEquals(cv.show(), "Cucurbitaceae sp. (IGC1034) 'Lekker Bek'")
        sp_nov = Taxon(rank=self.species, parent=self.plantae, nov_code='IGC1035')
        self.assertEquals(sp_nov.show(), 'Plantae sp. (IGC1035)')

    def test6_shows_australian_new(self):
        asterales = Taxon(rank=self.ordo, parent=self.plantae, epithet='Asterales')
        asteraceae = Taxon(rank=self.familia, parent=asterales, epithet='Asteraceae')
        gen_nov = Taxon(rank=self.genus, parent=asteraceae, nov_code='Aq520454')
        sp_nov = Taxon(rank=self.species, parent=gen_nov, nov_code='D.A.Halford Q811', nov_name='Shute Harbour')
        cv = Taxon(rank=self.cultivar, parent=sp_nov, epithet='Due di Denari')
        self.assertEquals(sp_nov.show(), 'Gen. (Aq520454) sp. Shute Harbour (D.A.Halford Q811)')
        self.assertEquals(gen_nov.show(), 'Gen. (Aq520454) sp.')
        self.assertEquals(cv.show(), "Gen. (Aq520454) sp. Shute Harbour (D.A.Halford Q811) 'Due di Denari'")


class TestDefaultData(BaubleTestCase):
    def setUp(self):
        from . import TaxonomyPlugin
        super().setUp()
        TaxonomyPlugin.install(import_defaults=True)
        
    def test_imported_taxa(self):
        objs = self.session.query(Taxon).all()
        self.assertEquals(len(objs), 203)
        beschorneria = self.session.query(Taxon).filter_by(epithet='Beschorneria').first()
        self.assertNotEquals(beschorneria, None)
        self.assertEquals(beschorneria.epithet, 'Beschorneria')

    def test_imported_ranks(self):
        obj = self.session.query(Rank).filter_by(id=4).first()
        self.assertNotEquals(obj, None)
        self.assertEquals(obj.name, 'ordo')
        objs = self.session.query(Rank).all()
        self.assertEquals(len(objs), 17)
