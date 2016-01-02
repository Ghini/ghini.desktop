# -*- coding: utf-8 -*-
#
# Copyright 2016 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.
#

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from bauble import db, meta


class StoredQueries(object):
    def __init__(self):
        self.__label = [''] * 11
        self.__tooltip = [''] * 11
        self.__query = [''] * 11
        ssn = db.Session()
        q = ssn.query(meta.BaubleMeta)
        stqrq = q.filter(meta.BaubleMeta.name.startswith(u'stqr_'))
        for item in stqrq:
            index = int(item.name[5:])
            self[index] = item.value
        ssn.close()
        self.page = 1

    def __repr__(self):
        return '[p:%d; l:%s; t:%s; q:%s' % (
            self.page, self.__label[1:], self.__tooltip[1:], self.__query[1:])

    def save(self):
        for index in range(1, 11):
            if self.__label[index] == '':
                continue
            print 'stqr_%02d' % index, self[index]

    def __getitem__(self, index):
        return u'%s:%s:%s' % (self.__label[index],
                              self.__tooltip[index],
                              self.__query[index])

    def __setitem__(self, index, value):
        self.page = index
        self.label, self.tooltip, self.query = value.split(':', 2)

    def __iter__(self):
        self.__index = 0
        return self

    def next(self):
        if self.__index == 10:
            raise StopIteration
        else:
            self.__index += 1
            return self[self.__index]

    @property
    def label(self):
        return self.__label[self.page]

    @label.setter
    def label(self, value):
        self.__label[self.page] = value

    @property
    def tooltip(self):
        return self.__tooltip[self.page]

    @tooltip.setter
    def tooltip(self, value):
        self.__tooltip[self.page] = value

    @property
    def query(self):
        return self.__query[self.page]

    @query.setter
    def query(self, value):
        self.__query[self.page] = value
