from bauble import db
from bauble.plugins import plants


def species_to_fix(s, create=False):
    gen_epithet, sp_epithet = s.split(' ', 1)
    return plants.Species.retrieve_or_create(
        ssn, {'object': 'taxon',
              'rank': 'species',
              'ht-epithet': gen_epithet,
              'epithet': sp_epithet,
              'ht-rank': 'genus'},
        create=create)


def species_to_add(s):
    return species_to_fix(s, create=True)


db.open("sqlite:////home/mario/.bauble/cuchubo-corrected.db")
ssn = db.Session()

import codecs
with codecs.open("/tmp/complete.csv", 'r', 'utf16') as f:
    keys = f.readline().strip().split('\t')
    for l in f.readlines():
        l = l.strip()
        values = [i.strip() for i in l.split("\t")]
        fields = dict(zip(keys, values))
        print fields['Name_submitted'], fields['Name_matched']

        obj = species_to_fix(fields['Name_submitted'])
        if obj is None:
            print fields['Name_submitted']
            continue
        gen_epithet, sp_epithet = fields['Name_matched'].split(' ')
        obj.sp = sp_epithet
        obj.sp_author = fields['Name_matched_author']
        print ("corrected %(Name_submitted)s to %(Name_matched)s "
               "%(Name_matched_author)s") % fields

        if (fields['Taxonomic_status'] == u'Synonym' and
                fields['Accepted_name']):
            accepted = species_to_add(fields['Accepted_name'])
            if accepted is None:
                print 'could not create ', fields['Accepted_name']
                continue
            accepted.sp_author = fields['Accepted_name_author']
            obj.accepted = accepted
            print ("set %(Name_matched)s %(Name_matched_author)s as synonym "
                   "of %(Accepted_name)s %(Accepted_name_author)s") % fields

ssn.commit()
