#!/bin/bash

# make sure we are in the project root dir
cd $(dirname $0)/..
# and that the pot dir exists
mkdir -p pot 

#------------------------------------------------------------------------
# Extract all the translatable strings and generate the message templates
#------------------------------------------------------------------------

# glade
xgettext --language=glade -o pot/glade.pot --from-code=utf-8 $(find bauble -name "*.glade")

# python
xgettext --language=Python -o pot/python.pot --from-code=utf-8 -k_ $(find bauble -name "*.py")

# documentation
sphinx-build -b gettext doc pot/

#------------------------------------------------------------------------
# merge all message templates into one
#------------------------------------------------------------------------
touch pot/messages.pot
rm pot/messages.pot
msgcat pot/*.pot > pot/messages.pot

#------------------------------------------------------------------------
# finally update all internationalization files
#------------------------------------------------------------------------
for po in $(find po -name \*.po)
do
    msgmerge -UNqs $po pot/messages.pot
done
