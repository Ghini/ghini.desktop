#!/bin/bash

# make sure we are in the project root dir
cd $(dirname $0)/..
# and that the pot dir exists
mkdir -p pot 

#------------------------------------------------------------------------
# Extract all the translatable strings and generate the message templates
#------------------------------------------------------------------------

# glade
echo -n 'doing glade files ... '
xgettext --language=glade -o pot/glade.pot --from-code=utf-8 $(find bauble -name "*.glade")
echo 'ok'

# python
echo -n 'doing python files ... '
pythonlist=$(mktemp)
find bauble -name "*.py" > $pythonlist
pygettext -X $pythonlist --escape -o pot/python.pot $(find bauble -name "*.py")
sed -i -e 's/CHARSET/utf-8/' pot/python.pot  # I do not know how to specify it on command line
echo 'ok'

# documentation, but not the api. (this goes in a different project)
#echo -n 'doing documentation files (excluding api.rst) ... '
#sphinx-build -b gettext doc pot/
#rm pot/api.pot
#echo 'ok'

#------------------------------------------------------------------------
# merge all message templates into one
#------------------------------------------------------------------------
touch pot/messages.pot
rm pot/messages.pot
echo -n 'now merging partial pot files ... '
msgcat pot/*.pot > pot/messages.pot
echo 'ok'

#------------------------------------------------------------------------
# finally update all internationalization files
#------------------------------------------------------------------------
echo -n 'finally update all internationalization files ... '
for po in $(find po -name \*.po)
do
    msgmerge -UNqs $po pot/messages.pot
done
echo 'ok'
