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
    idlist, cursor = [child for child in root]
    result = []
    for uuid in [i.text for i in idlist]:
        url = (base_format % {'form_id': form_id,
                              'api': 'downloadSubmission',
                              'host': host} +
               submission_format % {'group_name': 'plant_form',
                                    'uuid': uuid})
        reply = requests.get(url, auth=auth)
        root = ET.fromstring(reply.text)
        [data for data in root]
        [form for form in data]
        result.append(dict([(i.tag.replace('{http://opendatakit.org/submissions}', ''), i.text) for i in form]))
    return result
