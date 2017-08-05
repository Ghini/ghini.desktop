# -*- coding: utf-8 -*-
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
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

from requests.auth import HTTPDigestAuth
import requests
import xml.etree.ElementTree as ET

def get_submissions(host, form_id, user, pw):
    base_format = 'https://%(host)s/view/%(api)s?formId=%(form_id)s'
    submission_format = '[@version=null and @uiVersion=null]/%(group_name)s[@key=%(uuid)s]'
    auth = HTTPDigestAuth(user, pw)
    result = requests.get(base_format % {'form_id': form_id,
                                         'api': 'submissionList',
                                         'host': host},
                          auth=auth)
    root = ET.fromstring(result.text)
    idlist, cursor = root
    result = []
    for uuid in [i.text for i in idlist]:
        url = (base_format % {'form_id': form_id,
                              'api': 'downloadSubmission',
                              'host': host} +
               submission_format % {'group_name': 'plant_form',
                                    'uuid': uuid})
        reply = requests.get(url, auth=auth)
        root = ET.fromstring(reply.text)
        data, = root
        form, = data
        result.append(dict([(i.tag.replace('{http://opendatakit.org/submissions}', ''), i.text) for i in form]))
    return result
