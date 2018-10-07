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
        ('regnum', 0, '[.epithet] sp.', 'regnum'),
        ('ordo', 8, '[.epithet] sp.', 'ordo'),
        ('familia', 10, '[.epithet] sp.', 'familia'),
        ('subfamilia', 14, '[.epithet] sp.', 'subfamilia'),
        ('tribus', 16, '.epithet sp.', ''),
        ('subtribus', 18, '.epithet sp.', ''),
        ('genus', 20, '[.epithet] sp.', 'genus'),
        ('subgenus', 25, '.genus subg. .epithet sp.', ''),
        ('sectio', 30, '.genus sec. .epithet sp.', ''),
        ('subsectio', 35, '.genus subsec. .epithet sp.', ''),
        ('species', 40, '[.genus .epithet]', 'binomial'),
        ('subspecies', 45, '.binomial subsp. .epithet', ''),
        ('varietas', 50, '.binomial var. .epithet', ''),
        ('forma', 55, '.binomial f. .epithet', ''), ]
    for name, depth, shows_as, defines in ranks:
        p = Rank(name=name, depth=depth, shows_as=shows_as, defines=defines)
        self.session.add(p)
    self.session.commit()
    (self.regnum, self.ordo, self.familia, self.subfamilia, self.tribus,
     self.subtribus, self.genus, self.subgenus, self.sectio, self.subsectio,
     self.species, self.subspecies, self.varietas, self.forma
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
        p = Rank(name='Ordo', depth=8, shows_as='[.epithet] sp', defines='ordo')
        self.session.add(p)
        self.session.commit()

        q = self.session.query(Rank).all()
        self.assertEquals(len(q), 1)
        self.assertEquals(q[0], p)

    def test_can_create_rank_structure(self):
        ranks = [
            ('ordo', 8, '[.epithet] sp.', 'ordo'),
            ('familia', 10, '[.epithet] sp.', 'familia'),
            ('subfamilia', 14, '[.epithet] sp.', 'subfamilia'),
            ('tribus', 16, '.epithet sp.', ''),
            ('subtribus', 18, '.epithet sp.', ''),
            ('genus', 20, '[.epithet] sp.', 'genus'),
            ('subgenus', 25, '.genus subg. .epithet sp.', ''),
            ('sectio', 30, '.genus sec. .epithet sp.', ''),
            ('subsectio', 35, '.genus subsec. .epithet sp.', ''),
            ('species', 40, '[.genus .epithet]', 'binomial'),
            ('subspecies', 45, '.binomial subsp. .epithet', ''),
            ('varietas', 50, '.binomial var. .epithet', ''),
            ('forma', 55, '.binomial f. .epithet', ''), ]
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

    def test_shows_as_genus(self):
        annona = self.session.query(Taxon).filter_by(epithet='Annona').first()
        self.assertEquals(annona.show(), 'Annona sp.')
        tilioideae = self.session.query(Taxon).filter_by(epithet='Tilioideae').first()
        self.assertEquals(tilioideae.show(), 'Tilioideae sp.')
        
    def test_shows_as_species(self):
        annona = self.session.query(Taxon).filter_by(epithet='Annona').first()
        guanabana = Taxon(rank=self.species, parent=annona, epithet='muricata')
        self.session.add(guanabana)
        self.assertEquals(guanabana.show(), 'Annona muricata')

    def test_shows_as_subspecies(self):
        cucurbitales = Taxon(rank=self.ordo, parent=self.plantae, epithet='Cucurbitales')
        cucurbitaceae = Taxon(rank=self.familia, parent=cucurbitales, epithet='Cucurbitaceae')
        cucurbita = Taxon(rank=self.genus, parent=cucurbitaceae, epithet='Cucurbita')
        pepo = Taxon(rank=self.species, parent=cucurbita, epithet='pepo')
        cylindrica = Taxon(rank=self.varietas, parent=pepo, epithet='cylindrica')
        self.session.add_all([cucurbitales, cucurbitaceae, cucurbita, pepo, cylindrica])
        self.assertEquals(cylindrica.show(), 'Cucurbita pepo var. cylindrica')
        
