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

try:
    from bauble.i18n import _
except:
    _ = lambda x: x

# sorted dictionaries from the ITF2 document, to be used to populate list
# stores associated to combo boxes.

# section B:

accsta_dict = (
    (u'', ''),
    (u'C', _('Current accession in the living collection')),
    (u'D', _('Non‑current accession of the living collection due to death')),
    (u'T', _('Non‑current accession due to transfer to another record '
             'system, normally of another garden')),
    (u'S', _('Stored in a dormant state')),
    (u'O', _('Other accession status  - different from those above.')),
    )

acct_dict = (
    (u'', ''),
    (u'P', _('Whole plant')),
    (u'S', _('Seed or Spore')),
    (u'V', _('Vegetative part')),
    (u'T', _('Tissue culture ')),
    (u'O', _('Other')),
    )

# section C:

## this applies to `genhyb` and `sphyb`
hybrid_marker = (
    (u'', _('not a hybrid')),
    (u'H', _('H - hybrid formula')),
    (u'×', _('× - nothotaxon')),
    (u'+', _('+ - graft chimera')),
    )

## this applies to spql when only considering the taxon.
aggregate = (
    (u'', _('not a complex')),
    (u'agg.', _('aggregate taxon')),
    )

## this applies to spql when considering an accession associated to a
## complex taxon.
acc_spql = (
    (None, ''),  # do not transfer this field
    (u's. lat.', _('aggregrate species (sensu lato)')),
    (u's. str.', _('segregate species (sensu stricto)')),
    )

vlev_dict = (
    (None, ''),  # do not transfer this field
    (u'U', _('It is not known if the name of the plant has been checked by '
             'an authority.')),
    (u'0', _('The name of the plant has not been determined by any '
             'authority')),
    (u'1', _('The name of the plant has been determined by comparison with '
             'other named plants')),
    (u'2', _('The name of the plant has been determined by a taxonomist or '
             'other competent person using the facilities of a library '
             'and/or herbarium, or other documented living material')),
    (u'3', _('The name of the plant has been determined by a taxonomist who '
             'is currently or has been recently involved in a revision of '
             'the family or genus')),
    (u'4', _('The plant represents all or part of the type material on '
             'which the name was based, or the plant has been derived '
             'therefore by asexual propagation')),
    )

# section E:

# E.1 - Provenance Type Flag
prot_dict = (
    (None, ''),  # do not transfer this field
    (u'W', _('Accession of wild source')),
    (u'Z', _('Propagule(s) from a wild source plant')),
    (u'G', _("Accession not of wild source")),
    (u'U', _("Insufficient data to determine")),
    )
'A code to indicate the provenance of the accession'

# E.2 - Propagation History Flag
prohis_dict = (
    (None, ''),  # do not transfer this field
    (u'I', _('Individual wild plant(s)')),
    (u'S', _('Plant material arising from sexual reproduction (excluding '
             'apomixis)')),
    (u'SA', _('From open breeding')),
    (u'SB', _('From controlled breeding')),
    (u'SC', _('From plants that are isolated and definitely self-pollinated')),
    (u'V', _('Plant material derived asexually')),
    (u'VA', _('From vegetative reproduction')),
    (u'VB', _('From apomictic cloning (agamospermy)')),
    (u'U', _('Propagation history uncertain, or no information')),
    )
'A code to indicate the nature of the production of the plant material being '
'accessioned, for use in association with the previous field, Provenance Type'

# E.3 - Wild Provenance Status Flag
wpst_dict = (
    (None, ''),  # do not transfer this field
    ('Wild native', _('Endemic found within its indigenous range')),
    ('Wild non-native', _('Plant found outside its indigenous range')),
    ('Cultivated native', _('Endemic, cultivated and reintroduced or '
                            'translocated within indigenous range')),
    ('Cultivated non-native', _('cultivated, found outside indigenous range')),
    )
"A code to clarify the status of a recorded 'wild' provenance accession"

# E.5 - Donor Type Flag
dont_dict = (
    (u'E', _('Expedition')),
    (u'G', _('Gene bank')),
    (u'B', _('Botanic Garden or Arboretum')),
    (u'R', _('Other research, field or experimental station')),
    (u'S', _('Staff of this botanic garden')),
    (u'U', _('University Department')),
    (u'H', _('Horticultural Association or Garden Club')),
    (u'M', _('Municipal department')),
    (u'N', _('Nursery or other commercial establishment')),
    (u'I', _('Individual')),
    (u'O', _('Other')),
    (u'U', _('Unknown')),
    )
"A code to indicate the type of immediate donor from which the accession was "
"obtained.  This may not be necessarily be the original collector of wild "
"material"

# G.3 - Perennation Flag - Transfer code:  per
per_dict = (
    (None, ''),  # do not transfer this field
    (u'M', _('Monocarpic plants')),
    (u'MA', _('Annuals')),
    (u'MB', _('Biennials and short-lived perennials')),
    (u'ML', _('Long-lived monocarpic plants')),
    (u'P', _('Polycarpic plants')),
    (u'PD', _('Deciduous polycarpic plants')),
    (u'PE', _('Evergreen polycarpic plants')),
    (u'U', _('Uncertain which of the above applies.')),
    )
"A code to indicate the means of perennation, providing a means of noting"
"living plant accessions that require regular curatorial monitoring"

# G.4 - Breeding System
brs_dict = (
    (None, ''),  # do not transfer this field
    (u'M', _('\'Male\', defined as plants that do not produce functional '
             'female flowers')),
    (u'F', _('\'Female\', defined as plants that do not produce functional '
             'male flowers')),
    (u'B', _('The accession includes both \'male\' and \'female\' '
             'individuals as described above')),
    (u'Q', _('Dioecious plant of unknown sex')),
    (u'H', _('The accession reproduces sexually, and possesses '
             'hermaphrodite flowers or is monoecious')),
    (u'H1', _('The accession reproduces sexually, and possesses '
              'hermaphrodite flowers or is monoecious, but is known to be '
              'self-incompatible.')),
    (u'A', _('The accession reproduces by agamospermy')),
    (u'U', _('Insufficient information to determine breeding system')),
    )
"A code to indicate the breeding system of the accession."
