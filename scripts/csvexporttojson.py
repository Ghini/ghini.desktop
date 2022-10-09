#!/usr/bin/python
# -*- coding: utf-8 -*-
#
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

import json
import csv


def project(d, fields):
    '''project dictionary on selected fields.
    '''
    result = {}
    for k, kk in fields:
        value = d.get(k)
        if value:
            result[kk] = value
    return result


def latinlowestof(record, ranks):
    '''latin name of lowest rank in record

    ranks is a list of pairs, record and latin names.
    '''

    for k, latin in ranks:
        if record[k]:
            return latin
    return 'familia'


def split_and_apply(s):
    """parse input string and evaluate it

    the input string looks like 'value | f1 | f2 | ...'
    this function retrieves the value and applies all functions to it,
    left to right

    >>> split_and_apply('test |capitalize')
    'Test'
    >>> split_and_apply('Test |lower')
    'test'
    >>> split_and_apply('Test | upper')
    'TEST'
    >>> split_and_apply('Test | __len__')
    4
    >>> split_and_apply('Test | upper | __len__')
    4
    """

    if s.find('|') == -1:
        return s
    v, fs = [i.strip() for i in s.split('|', 1)]
    for f in [i.strip() for i in fs.split('|')]:
        f = getattr(v, f)
        v = f()
    return v


def main(config_file, input_stream, output_stream, want_taxonomy=False):
    '''read the input and write its content as json objects

    the input stream contains csv data.
    the first line contains the headers.
    all subsequent lines are comma separated, values are double quoted.

    we first scan the input, collecting objects as we go.
    several objects we will meet multiple times,
    so we put them in a set.
    then we pull things out of the set and we produce the output.
    '''

    import configparser
    import codecs
    config = configparser.RawConfigParser()
    config.readfp(codecs.open(config_file, 'r', 'utf-8'))

    input_stream = codecs.open(args.input)
    output_stream = codecs.open(args.output, 'w', 'utf-8')

    r = csv.reader(input_stream)

    header = next(r)
    # we don't want to repeat items, so we are storing the objects in a set.
    # they must be tuples because they must be indexable.
    result = set()
    for line in r:

        record = dict(list(zip(header, line)))

        ## the following is still hard coded and should be done otherwise
        for k in ['Genero', 'Subtribu', 'Tribu',
                  'Subfamilia', 'Familia']:
            record[k] = record[k].capitalize()

        record['Especie'] = record['Especie'].lower()
        ## end

        family = project(record, [('Familia', 'epithet')])
        family.update({'rank': 'familia'})

        subfamily = project(record, [('Subfamilia', 'epithet'),
                                     ('Familia', 'ht-epithet')])
        subfamily.update({'object': 'taxon',
                          'rank': 'subfamilia',
                          'ht-rank': 'familia'})

        tribe = project(record, [('Tribu', 'epithet'),
                                 ('Familia', 'ht-epithet'),
                                 ('Subfamilia', 'ht-epithet'),
                                 ])
        tribe.update({'object': 'taxon',
                      'rank': 'tribus'})
        tribe['ht-rank'] = latinlowestof(
            record, [
                ('Subfamilia', 'subfamilia'),
                ('Familia', 'familia')])

        subtribe = project(record, [('Subtribu', 'epithet'),
                                    ('Familia', 'ht-epithet'),
                                    ('Subfamilia', 'ht-epithet'),
                                    ('Tribu', 'ht-epithet'),
                                    ])
        subtribe.update({'object': 'taxon',
                         'rank': 'subtribus'})
        subtribe['ht-rank'] = latinlowestof(
            record, [
                ('Tribu', 'tribus'),
                ('Subfamilia', 'subfamilia'),
                ('Familia', 'familia')])

        genus = project(record, [('Genero', 'epithet'),
                                 ('Familia', 'ht-epithet'),
                                 ('Subfamilia', 'ht-epithet'),
                                 ('Tribu', 'ht-epithet'),
                                 ('Subtribu', 'ht-epithet'),
                                 ])
        genus.update({'object': 'taxon',
                      'rank': 'genus'})
        genus['ht-rank'] = latinlowestof(
            record, [
                ('Subtribu', 'subtribus'),
                ('Tribu', 'tribus'),
                ('Subfamilia', 'subfamilia'),
                ('Familia', 'familia')])

        species = project(record, [('Especie', 'epithet'),
                                   ('Familia', 'ht-epithet'),
                                   ('Subfamilia', 'ht-epithet'),
                                   ('Tribu', 'ht-epithet'),
                                   ('Subtribu', 'ht-epithet'),
                                   ('Genero', 'ht-epithet'),
                                   ('CITES', 'cites'),
                                   ('Habito', 'habit'),
                                   ('Autor', 'author'),
                                   ])
        species.update({'object': 'taxon',
                        'rank': 'species'})
        species['ht-rank'] = latinlowestof(
            record, [
                ('Genero', 'genus'),
                ('Subtribu', 'subtribus'),
                ('Tribu', 'tribus'),
                ('Subfamilia', 'subfamilia'),
                ('Familia', 'familia')])

        if want_taxonomy:
            result.add(tuple(family.items()))
            result.add(tuple(subfamily.items()))
            result.add(tuple(tribe.items()))
            result.add(tuple(subtribe.items()))
            result.add(tuple(genus.items()))
            result.add(tuple(species.items()))

        accession = {'object': 'accession'}
        accession['code'] = ('000000' + record['Item'])[-6:]
        accession.update(project(record, [('Procedencia', 'prov-type'),
                                          ]))

        if species.get('epithet') and genus.get('epithet'):
            accession['taxon'] = genus['epithet'] + ' ' + species['epithet']
            accession['rank'] = 'species'
        elif genus.get('epithet'):
            accession['taxon'] = genus['epithet']
            accession['rank'] = 'genus'
        elif subtribe.get('epithet'):
            accession['taxon'] = subtribe['epithet']
            accession['rank'] = 'subtribus'
        elif tribe.get('epithet'):
            accession['taxon'] = tribe['epithet']
            accession['rank'] = 'tribus'
        elif subfamily.get('epithet'):
            accession['taxon'] = subfamily['epithet']
            accession['rank'] = 'subfamilia'
        elif family.get('epithet'):
            accession['taxon'] = family['epithet']
            accession['rank'] = 'familia'

        plant = {'object': 'plant'}
        plant['code'] = ('000000' + record['Item'])[-6:] + ".1"
        plant.update(project(record, [('Ubicación', 'location'),
                                      ('Situación', 'status'),
                                      ]))

        result.add(tuple(accession.items()))
        result.add(tuple(plant.items()))

    output_stream.write("[")
    for n, i in enumerate(result):
        json.dump(dict(i), output_stream, sort_keys=True)
        if n < len(result) - 1:
            output_stream.write(",\n ")
    output_stream.write("]")


if __name__ == '__main__':
    "we read the options, then invoke main() with them"

    import argparse
    parser = argparse.ArgumentParser(
        description='convert any CSV file to a list of json objects.')
    parser.add_argument('config', nargs=1,
                        help='the config file describing the CSV input')
    parser.add_argument('input', nargs=1,
                        help='the CSV input file')
    parser.add_argument('output', nargs=1,
                        help='the json output file')
    parser.add_argument('--want-taxonomy', action="store_true", default=False,
                        help='do we output all taxonomic information?')

    args = parser.parse_args()
    main(args.config, args.input, args.output, args.want_taxonomy)
