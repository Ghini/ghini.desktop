#what has changed?
#------------------
#Accession.date added
#Accession.source_type - is not an EnumCol, shouldn't be any problems
#except that any 'NoneType' string should be changed to None
#Accession.prov_type - change '<not set>' to None
#Accession.wild_prov_status - change '<not set>' to None
#Donor.donor_type - change '<not set>' to None
#Plant.acc_type - change '<not set>' to None
#Plant.acc_status - change '<not set>' to None
#PlantHistory - though this table didn't exist so there is nothing
#to migrate

# can i alter tables in the database or only work on dumped text files

