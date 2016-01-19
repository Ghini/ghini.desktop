# -*- coding: utf-8 -*-
#
# Copyright 2016 Mario Frasca <mario@anche.no>.
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

# sorted dictionaries from the ITF2 document, to be used to populate list
# stores associated to combo boxes.

# section B:

accsta_dict = (
    (u'', ''),
    (u'C', 'Current accession in the living collection'),
    (u'D', 'Non‑current accession of the living collection due to death'),
    (u'T', ('Non‑current accession due to transfer to another record '
            'system, normally of another garden')),
    (u'S', 'Stored in a dormant state'),
    (u'O', 'Other accession status  - different from those above.'),
    )

acct_dict = (
    (u'', ''),
    (u'P', 'Whole plant'),
    (u'S', 'Seed or Spore'),
    (u'V' 'Vegetative part'),
    (u'T' 'Tissue culture '),
    (u'O', 'Other'),
    )

# section C:

## this applies to `genhyb` and `sphyb`
hybrid_marker = (
    (u'', 'not a hybrid'),
    (u'H', 'H - hybrid formula'),
    (u'×', '× - nothotaxon'),
    (u'+', '+ - graft chimera'),
    )

## this applies to spql when only considering the taxon.
aggregate = (
    (u'', 'not a complex'),
    (u'agg.', 'aggregate taxon'),
    )

## this applies to spql when considering an accession associated to a
## complex taxon.
acc_spql = (
    (u'', ''),
    (u's. lat.', 'aggregrate species (sensu lato)'),
    (u's. str.', 'segregate species (sensu stricto)'),
    )

vlev_dict = (
    (u'', ''),
    (u'U', ('It is not known if the name of the plant has been checked by '
            'an authority.')),
    (u'0', ('The name of the plant has not been determined by any '
            'authority')),
    (u'1', ('The name of the plant has been determined by comparison with '
            'other named plants')),
    (u'2', ('The name of the plant has been determined by a taxonomist or '
            'other competent person using the facilities of a library '
            'and/or herbarium, or other documented living material')),
    (u'3', ('The name of the plant has been determined by a taxonomist who '
            'is currently or has been recently involved in a revision of '
            'the family or genus')),
    (u'4', ('The plant represents all or part of the type material on '
            'which the name was based, or the plant has been derived '
            'therefore by asexual propagation')),
    )

prot_dict = (
    (u'', ''),
    (u'W', 'Accession of wild source'),
    (u'Z', 'Propagule(s) from a wild source plant in cultivation'),
    (u'G', 'Accession not of wild source'),
    (u'U', ('Insufficient data to determine')),
    )

prohis_dict = (
    (u'', ''),
    (u'I', 'Individual wild plant(s)'),
    (u'S', ('Plant material arising from sexual reproduction (excluding '
            'apomixis)')),
    (u'SA', 'From open breeding'),
    (u'SB', 'From controlled breeding'),
    (u'SC', 'From plants that are isolated and definitely self-pollinated'),
    (u'V', 'Plant material derived asexually'),
    (u'VA', 'From vegetative reproduction '),
    (u'VB', 'From apomictic cloning (agamospermy)'),
    (u'U', 'Propagation history uncertain, or no information.'),
    )

dont_dict = (
    (u'E', 'Expedition'),
    (u'G', 'Gene bank'),
    (u'B', 'Botanic Garden or Arboretum'),
    (u'R', 'Other research, field or experimental station'),
    (u'S', 'Staff of this botanic garden'),
    (u'U', 'University Department'),
    (u'H', 'Horticultural Association or Garden Club'),
    (u'M', 'Municipal department'),
    (u'N', 'Nursery or other commercial establishment'),
    (u'I', 'Individual'),
    (u'O', 'Other'),
    (u'U', 'Unknown'),
    )

per_dict = (
    (u'M', 'Monocarpic plants'),
    (u'MA', 'Annuals'),
    (u'MB', 'Biennials and short-lived perennials'),
    (u'ML', 'Long-lived monocarpic plants'),
    (u'P', 'Polycarpic plants'),
    (u'PD', 'Deciduous polycarpic plants'),
    (u'PE', 'Evergreen polycarpic plants'),
    (u'U', 'Uncertain which of the above applies.'),
    )

brs_dict = (
    (u'M', ('\'Male\', defined as plants that do not produce functional '
            'female flowers')),
    (u'F', ('\'Female\', defined as plants that do not produce functional '
            'male flowers')),
    (u'B', ('The accession includes both \'male\' and \'female\' '
            'individuals as described above')),
    (u'Q', ('Dioecious plant of unknown sex')),
    (u'H', ('The accession reproduces sexually, and possesses '
            'hermaphrodite flowers or is monoecious')),
    (u'H1', ('The accession reproduces sexually, and possesses '
             'hermaphrodite flowers or is monoecious, but is known to be '
             'self-incompatible.')),
    (u'A', ('The accession reproduces by agamospermy')),
    (u'U', ('Insufficient information to determine breeding system.')),
    )
