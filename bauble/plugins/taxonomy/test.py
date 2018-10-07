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
            ('ordo', 8, '[.epithet] sp', 'ordo'),
            ('familia', 10, '[.epithet] sp', 'familia'),
            ('subfamilia', 14, '[.epithet] sp', 'subfamilia'),
            ('tribus', 16, '.epithet sp', ''),
            ('subtribus', 18, '.epithet sp', ''),
            ('genus', 20, '[.epithet] sp', 'genus'),
            ('subgenus', 25, '.genus subg. .epithet sp', ''),
            ('sectio', 30, '.genus sec. .epithet sp', ''),
            ('subsectio', 35, '.genus subsec. .epithet sp', ''),
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

    def test_create_malvaceae_structure(self):
        ranks = [
            ('regnum', 0, '[.epithet] sp', 'regnum'),
            ('ordo', 8, '[.epithet] sp', 'ordo'),
            ('familia', 10, '[.epithet] sp', 'familia'),
            ('subfamilia', 14, '[.epithet] sp', 'subfamilia'), ]
        for name, depth, shows_as, defines in ranks:
            p = Rank(name=name, depth=depth, shows_as=shows_as, defines=defines)
            self.session.add(p)
        self.session.commit()
        regnum, ordo, familia, subfamilia = self.session.query(Rank).order_by(Rank.depth).all()
        # rank, id, epithet, parent_id, accepted_id
        taxa = [
            (regnum, 0, 'Plantae', 0, None), 
            (ordo, 1, 'Malvales', 0, None), 
            (familia, 2, 'Malvaceae', 1, None),
            (subfamilia, 3, 'Sterculioideae', 2, None), 
            (subfamilia, 4, 'Tilioideae', 2, None),
            (familia, 5, 'Sterculiaceae', 1, 3), 
            (familia, 6, 'Tiliaceae', 1, 4), ]
        for rank, id, epithet, parent_id, accepted_id in taxa:
            p = Taxon(rank=rank, id=id, epithet=epithet, parent_id=parent_id, accepted_id=accepted_id)
            self.session.add(p)
        self.session.commit()
        

class TestingRepresentation(BaubleTestCase):
    def setUp(self):
        super().setUp()
        ranks = [
            ('regnum', 0, '[.epithet] sp', 'regnum'),
            ('ordo', 8, '[.epithet] sp', 'ordo'),
            ('familia', 10, '[.epithet] sp', 'familia'),
            ('subfamilia', 14, '[.epithet] sp', 'subfamilia'),
            ('tribus', 16, '.epithet sp', ''),
            ('subtribus', 18, '.epithet s', ''),
            ('genus', 20, '[.epithet] sp', 'genus'),
            ('subgenus', 25, '.genus subg. .epithet sp', ''),
            ('sectio', 30, '.genus sec. .epithet sp', ''),
            ('subsectio', 35, '.genus subsec. .epithet sp', ''),
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
        
    def test0_creation(self):
        self.assertEquals(self.genus.name, 'genus')
        annona = self.session.query(Taxon).filter_by(epithet='Annona').first()
        self.assertEquals(annona.epithet, 'Annona')

    def test_shows_as_genus(self):
        annona = self.session.query(Taxon).filter_by(epithet='Annona').first()
        self.assertEquals(annona.show(), 'Annona sp.')
        tilioideae = self.session.query(Taxon).filter_by(epithet='Tilioideae').first()
        self.assertEquals(annona.show(), 'Tilioideae sp.')
        
