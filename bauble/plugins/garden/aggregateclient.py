#
# Copyright 2017 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple, cast

import requests
from requests.auth import HTTPDigestAuth


def get_submissions(
    user: str, pw: str, host: str, form_id: str, to_skip: Optional[List[str]] = None
) -> Optional[List[Dict[str, Any]]]:
    if to_skip is None:
        to_skip = []
    base_format = "https://%(host)s/view/%(api)s?formId=%(form_id)s"
    submission_format = (
        "[@version=null and @uiVersion=null]/%(group_name)s[@key=%(uuid)s]"
    )
    auth = HTTPDigestAuth(user, pw)
    response = requests.get(
        base_format % {"form_id": form_id, "api": "submissionList", "host": host},
        auth=auth,
    )
    if not response.ok:
        return None
    root = ET.fromstring(response.text)
    idlist = root[0]
    result: List[Dict[str, Any]] = []
    for uuid in [i.text for i in idlist]:
        if uuid in to_skip:
            continue
        try:
            reply = requests.get(
                (
                    base_format
                    % {
                        "form_id": form_id,
                        "api": "downloadSubmission",
                        "host": host,
                    }
                    + submission_format % {"group_name": "plant_form", "uuid": uuid}
                ),
                auth=auth,
            )
        except requests.exceptions.ConnectionError:
            continue
        root = ET.fromstring(reply.text)
        data = root[0]  # media may follow
        form = data[0]
        item: Dict[str, Any] = {re.sub(r"{.*}(.*)", r"\1", i.tag): i.text for i in form}
        item["meta:uuid"] = uuid
        result.append(item)
        for key in list(item.keys()):
            if not key.endswith("_repeat"):
                continue
            del item[key]
            prefix = key[:-7]
            item[prefix] = [i[0].text for i in form if i.tag.endswith(key)]
        item["media"] = cast(Dict[str, Tuple[str, str]], {})
        for _i, media_element in enumerate(root[1:]):
            filename, hash, url = media_element
            item["media"][filename.text] = (url.text, hash.text)
    return result


def get_image(user: str, pw: str, url: str, path: str) -> None:
    auth = HTTPDigestAuth(user, pw)
    pic = requests.get(url, stream=True, auth=auth)
    if pic.status_code == 200:
        with open(path, "wb") as f:
            for chunk in pic.iter_content(1024):
                f.write(chunk)
