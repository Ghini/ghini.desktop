#!/usr/bin/env python

import os, re, glob, shutil

OUT_PATH = 'new'

if not os.path.exists(OUT_PATH):
    os.mkdir('new')

def open_outfile(filename):
    out_filename = '%s%s%s' % (OUT_PATH, os.sep, filename)
#    if os.path.exists(out_filename):
#        response =raw_input('%s exists. You you want to overwrite it? (y/n): '\
#                            % out_filename)
#        if response in ('n', 'N'):        
#            sys.exit(1)
    return open(out_filename, 'w')            


def build_line_regex(columns):
    rx_str = ""
    for c in columns:
        rx_str += '(?P<%s>(?P<%s_quote>")?.*?(?(%s_quote)")),' %  (c,c,c)
    rx_str = rx_str[:-1] + '$' # replace the last comma with the EOL marker
    return re.compile(rx_str)


def migrate_genus(filename):
    columns = ("id","author","notes","hybrid","synonymID","familyID","genus")
    rx = build_line_regex(columns)
    
    genus_out = open_outfile(filename)
    genus_out.write('"id","author","notes","hybrid","familyID","genus"\n')
    genus_tmpl = '%(id)s,%(author)s,%(notes)s,%(hybrid)s,%(familyID)s,'\
                 '%(genus)s\n'    
    syn_out = open_outfile('GenusSynonym.txt')
    syn_out.write('"genusID","synonymID"\n')
    synID = 1
    for line in open(filename).readlines()[1:]:
        m = rx.match(line).groupdict()
        # these genera have been removed b/c of conflicts in the name,
        # if you had species that used these genera then sorry for you
        removed_genera = ("15846","15845","16614","19390","11264","22830")
        if m['id'] in removed_genera:
            print 'removed genus %s: %s' % (m['genus'][1:-2], m['id'])
            continue
#        print m
        synonym = m.pop('synonymID')
        if synonym != '""':            
            syn_out.write('%s,%s\n' % (m['id'], synonym))
        genus_out.write(genus_tmpl % m)
       


def migrate_species(filename):
    columns = ("id","sp","notes","isp","id_qual","vernacular_name",
                "sp_author","isp_rank","isp_author","genusID","cv_group",
                "sp_qual","sp_hybrid")
    rx = build_line_regex(columns)
    species_out = open_outfile('Species.txt')
    species_out.write('"id","sp","notes","isp","id_qual",'\
                      '"default_vernacular_nameID",'\
                      '"sp_author","isp_rank","isp_author","genusID",'\
                      '"cv_group","sp_qual","sp_hybrid"\n')
    species_template = '%(id)s,%(sp)s,%(notes)s,%(isp)s,%(id_qual)s,'\
                       '%(default_vernacular_nameID)s,%(sp_author)s,'\
                       '%(isp_rank)s,%(isp_author)s,%(genusID)s,'\
                       '%(cv_group)s,%(sp_qual)s,%(sp_hybrid)s\n'
    vernac_out = open_outfile('VernacularName.txt')
    vernac_out.write('"id","name","language","speciesID"\n')
    
    vid = 1
    for line in open(filename).readlines()[1:]:
        m = rx.match(line).groupdict()
        if m['id'] == '276':
            print m
        m['default_vernacular_nameID'] = m.pop('vernacular_name')
        #print m['default_vernacular_nameID']
        if m['default_vernacular_nameID'] != '""':
            vernac_out.write('%s,%s,"English",%s\n' %
                             (vid, m.pop('default_vernacular_nameID'),m['id']))
            m['default_vernacular_nameID'] = vid
            vid += 1
        species_out.write(species_template % m)

            
            

migration_map = {'Species.txt': migrate_species,
                 'Genus.txt': migrate_genus}

for f in glob.glob("*.txt"):
    if f in migration_map:
        migration_map[f](f)
    else:
        shutil.copyfile(f, '%s%s%s' % (OUT_PATH, os.sep, f))
        
