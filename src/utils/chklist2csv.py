#!/usr/bin/python


# a plant class with support for parsing a plant name string
# to contruct the object

import re

class Plant:
    def __init__(self, genus=None, species=None, isp_rank=None, 
                 isp=None, cv=None):
        self.genus = genus or ""
        self.species = species or ""
        self.species_author = ""
        self.isp_rank = isp_rank or ""
        self.isp_author =  ""
        self.isp = isp or ""
        self.cv = cv or ""
        self.is_cv = '' # HACK for this file only
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
            (?P<hybrid>x?)\s?              # hybrid sign
            (?P<species>[\w-]*)\s?     # match the species
            (?P<author>.*)""",
            speciesPart, re.VERBOSE)

        self.genus = m.group("genus")
        self.species = m.group("species")
        self.hybrid = m.group("hybrid")
        #self.species_author = unicode(m.group("author"), 'utf-8')
        self.species_author = unicode(m.group("author"), 'latin-1')
        #print self.species_author.encode('latin-1')
        
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
            self.isp_author=m.group("isp_author")

    # return a dict with key, value pairs for each member that has a value
    # don't return key/values if the string is ""
    #http://vsbabu.org/mt/archives/2003/02/13/joy_of_python_classes_and_dictionaries.html
    #return dict([(k, v) for (k, v) in o.__dict__.items if not k.startswith('_'+o.__class__.__name__)])
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
        str = self.genus
        if self.hybrid:
            str += " " + "x"
        if self.species is not None:            
            str += " " + self.species
        else: str += " sp."
        if self.isp_rank is not None:
            str += " " + self.isp_rank + " " + self.isp
        if self.cv is not None:
            str += " " + self.cv
            
        return str

    # should be able to set field separator, field encloser, and some fields
    # should be options like family, authors, hyrbid, etc..
    def csv(self, with_family=False):
        """
        print out in comma separated values format with the following fields:
        genus, species, species_author, isp_rank, isp, isp_author, cv, hybrid
        """        
        csv = ""
        ft = "," # field terminated
        if with_family is True:
            csvStr += self.family + ft
        csv += self.genus + ft + self.species + ft + \
               self.species_author.encode('latin-1') + ft + self.isp_rank +ft+\
               self.isp + ft + self.isp_author
        if self.cv is not "":
            csv += ft + " cv. " + self.cv
        else: csv += ft
        csv += ft + self.hybrid
        return csv
    # end Plant class


###################################################


# first parse the kew_genera.txt file for the genus id->name map
gen_dict = {}
missing = []
bad_lines = []
for line in open("kew_genera.txt").readlines():
    line = line.strip()
    if line == "": continue
    regex = re.compile('"(?P<id>.*?)","(?P<hybrid>.*?)","(?P<genus>.*?)",' + \
                       '"(?P<author>.*?)","(?P<syn>.*?)","(?P<fam_id>.*?)"')
    m = regex.match(line)    
    if m is not None:
        gen_dict[m.group('genus')] = m.group('id')
    else:
        # catch first line, should probably do somethi
        # ng more about this in case it really is a problem
        bad_lines.append(line)
        #print "no match: " + line

# print out a first line since it will be skipped
print "--"
family = None
for line in open("belize_plants.txt").readlines():    
    line = line.strip()    
    if line == "": continue
    cultivated = "n"
    if line.find(" ") == -1 or line.find(":") != -1:
        family = line
        continue        
    elif line.startswith('*'):        
        cultivated = "y"
        line = line[1:]
        continue # ******************* for now skip cultivated material
    p = Plant()
    p.match(line)
    
    #TODO: need to look up the namesof the genus and family
    if p.genus in missing:
        continue
    elif not gen_dict.has_key(p.genus):
        #print "could not find: " + p.genus
        missing.append(p.genus)
    elif p.species == "":
        bad_lines.append(line)
        continue # skip Prescottia sp. style names
    else:        
        p.genus = gen_dict[p.genus]
        print p.csv()
        
print "*** could not find the following genera: "
for m in missing:
    print m

print "*** could do anything with the following lines : "
for b in bad_lines:
    print b
    
        
    
