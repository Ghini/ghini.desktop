import bauble.plugins.garden.aggregateclient
import os.path
import datetime
import json

bauble.plugins.garden.aggregateclient.get_submissions('ghini-collect.appspot.com', 'plant_form_r', '', '')
r = bauble.plugins.garden.aggregateclient.get_submissions('ghini-collect.appspot.com', 'plant_form_r', user, pw)

for item in r:

    accession = {"object": "accession", "private": false, "species": "Zzz sp"}
    plant = {"object": "plant", "code": "1", "memorial": false, "quantity": 1}
    accession['code'] = item['acc_no_scan'] or item['acc_no_typed']
    plant['accession'] = accession['code']
    if item['location']:
        plant['location'] = item['location']
    if item['species']:
        accession['species'] = item['species']
    # should create a change object:
    if False:
        datetime.datetime.strptime(item['end'][:19], '%Y-%m-%dT%H:%M:%S')
    # should import pictures:
    if False:
        for p in item['photo']:
            url, md5 = r[0]['media'][i]
            path = os.path.separator.join('home', 'mario', 'tmp', 'PlantPictures', p)
            bauble.plugins.garden.aggregateclient.get_image(user, pw, url, path)
