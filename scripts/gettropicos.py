#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
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


def getTropicos(epithet):
    import requests
    r = requests.post(
        "http://tropicos.org/NameMatching.aspx",
        data={"__EVENTTARGET": "",
              "__EVENTARGUMENT": "",
              "ctl00$MainContentPlaceHolder$ctl01": "Match Names"},
        files={"ctl00$MainContentPlaceHolder$fileUploadControl":
               "FullNameNoAuthors\n%s" % epithet})
    header, row = [i.split('\t') for i in r.text.strip().split("\n")]
    return dict((k[6:].strip(), v.strip())
                for (k, v) in zip(header + ['OutputQuery'], row + [epithet])
                if k.startswith('Output') and not k == 'OutputHowMatched')


if __name__ == '__main__':
    import sys
    print getTropicos(' '.join(sys.argv[1:]))
