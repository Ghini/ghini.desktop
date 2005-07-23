#!/usr/bin/python

import sys, re, csv

data_dir = '/home/brett/devel/bauble/data/'
families_file = data_dir + 'csv/Families.txt'
genera_file = data_dir + 'csv/Genera.txt'
checklist_file = data_dir + 'old/belize_plants.txt'
plantname_columns='"genusID","sp","sp_author","isp_rank","isp","isp_author","sp_hybrid"'

# synonyms to use for the checklist genera
#generic_synonyms = {'Adenocalymna', Adenocalymma Mart. ex Meisn.

# a plant class with support for parsing a plant name string
# to contruct the object
class Plant:
    def __init__(self, genus=None, species=None, isp_rank=None, 
                 isp=None, cv=None):
        self.genus = genus or ""
        self.species = species or ""
        self.species_author = ""
        self.isp_rank = isp_rank or ""
        self.isp_author =  ""
        self.isp = isp or ""
#        self.cv = cv or ""
#        self.is_cv = '' # HACK for this file only
        self.hybrid = ''

    def match(self, plantName):        
        partsList = re.split("(?:subsp\.)+|(?:var\.)+", plantName)
        speciesPart = partsList[0].strip()

        # ** match species part
        # look for .sp, meaning it is not identified and should only
        # set the genus
        if speciesPart.find(" sp.") != -1:
            self.genus = re.match("(?P<genus>[\w]*)\s+",
                                  speciesPart).group("genus");
            return

        m = re.match(
            """(?P<genus>[\w]*)\s+     # match the genus
            (?P<hybrid>x?)\s?          # hybrid sign
            (?P<species>[\w-]*)\s?     # match the species
            (?P<author>.*)""",
            speciesPart, re.VERBOSE)

        self.genus = m.group("genus")
        self.species = m.group("species")
        self.hybrid = m.group("hybrid")
        self.species_author = unicode(m.group("author"), 'utf-8')
        
        # check for isp_rank
        if plantName.find("subsp.") != -1:
            self.isp_rank = "subsp."
        elif plantName.find("var.") != -1:
            self.isp_rank = "var."
            
        if self.isp_rank is not "":
            ispPart = partsList[1].strip();
            m = re.match(
                """\A(?P<isp>[\w]*)\s?
                (?P<isp_author>.*)""", ispPart, re.VERBOSE)            
            self.isp = m.group("isp")
            self.isp_author = unicode(m.group("isp_author"), 'utf-8')

    # return a dict with key, value pairs for each member that has a value
    # don't return key/values if the string is ""
    #http://vsbabu.org/mt/archives/2003/02/13/joy_of_python_classes_and_dictionaries.html
    #return dict([(k, v) for (k, v) in o.__dict__.items if not k.startswith('_'+o.__class__.__name__)])
    # TODO: i'm not sure if this works
    def dict(self):
        
        """Return a dictionary from object that has public
        variable -> key pairs
        """
        dict = {}
        #Joy: all the attributes in a class are already in __dict__
        privatePrefix = "_" + self.__class__.__name__
        for elem in self.__dict__.keys():
            if elem.find(privatePrefix) == 0:
                continue
                #We discard private variables, which are automatically
                #named _ClassName__variablename, when we define it in
                #the class as __variablename
            elif self.__dict__[elem] != "":
                try:
                    #dict[elem] = self.__dict__[elem].encode("latin-1")
                    dict[elem] = self.__dict__[elem]
                except:
                    print dict[elem]

                #dict[elem] = str(self.__dict__[elem]).encode("latin-1")
        return dict

    def __str__(self):
        s = self.genus
        if self.hybrid:
            s += " " + "x"
        if self.species is not None:            
            s += " " + self.species
        else: s += " sp."
        if self.isp_rank is not None:
            s += " " + self.isp_rank + " " + self.isp
#        if self.cv is not None:
#            s += " " + self.cv
            
        return s.strip()

    # should be able to set field separator, field encloser, and some fields
    # should be options like family, authors, hyrbid, etc..
    def csv(self, with_family=False):
        """
        print out in comma separated values format with the following fields:
        genus, species, species_author, isp_rank, isp, isp_author, cv, hybrid
        """        
        csv = ""
        ft = "," # field terminated
        enclosed = '"' # field enclosed
        field = lambda x: '%s%s%s' % (enclosed, x, enclosed)
        if with_family is True:
            csvStr += field(self.family) + ft
        if isinstance(self.genus, int):
            csv += str(self.genus) + ft
        else: csv+= field(self.genus) + ft

        try:
            csv += field(self.species) + ft + \
                   field(self.species_author.encode('utf-8')) + ft + \
                   field(self.isp_rank)  + ft + \
                   field(self.isp) + ft + field(self.isp_author.encode('utf-8'))
        except UnicodeDecodeError, e:
            print sys.stderr.write(e)
            raise
               
        # there are no cultivars in the belize checklist
#        if self.cv is not "":
#            csv += ft + field(" cv. " + self.cv)
#        else: 
#            csv += ft+ field('') + ft
        csv += ft + field(self.hybrid)
        #if self.hybrid is not '':
        #    csv += ft + 'True'
        #else: 
        #    csv += ft
        return csv
    # end Plant class


###################################################


# first parse the kew_genera.txt file for the genus id->name map,
# TODO: there is one genus in the file that has a duplicate name, find it
# and make sure that we don't use it in the checklist
gen_dict = {}
missing = {}
bad_lines = []

for line in csv.reader(open(genera_file)):
    gen_dict[line[2]] = line[0]

# print out a first line since it will be skipped
print plantname_columns
family = None
for line in open(checklist_file).readlines():    
    line = line.strip()    
    if line == "": continue
    cultivated = "n"
    if line.find(" ") == -1 or line.find(":") != -1:
        family = line
        continue        
    elif line.startswith('*'):        
        cultivated = "y"
        line = line[1:]
        #continue # ******************* for now skip cultivated material
    p = Plant()
    p.match(line)
    
    if p.genus not in gen_dict:
        if p.genus not in missing:
            missing[p.genus] = []
        missing[p.genus].append(str(p))
    elif p.species == "":
        bad_lines.append(line)
        continue # skip Prescottia sp. style names
    else:        
        p.genus = int(gen_dict[p.genus])
        print p.csv()
        

if len(missing) > 0:
    sys.stderr.write("******* could not find the following genera *******\n")
for gen, sp in missing.iteritems():
    sys.stderr.write('%s: %s\n' % (gen, sp))


if len(bad_lines) > 0:
    sys.stderr.write('******* could do anything with the following lines: *******\n')
for b in bad_lines:
    sys.stderr.write(b + '\n')
    #print b
    
        
    
