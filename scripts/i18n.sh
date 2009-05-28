#!/bin/bash

# Extract all the translatable strings and generate the message template

# Extract all the translatable strings from the glade files
find ./bauble -name "*.glade" -exec intltool-extract --type=gettext/glade {} \;

# Create the message.pot file from the python and .glade.h files
xgettext -k_ -kN_ -o messages.pot `find ./bauble -name "*.py" -o -name *.h`

#
# Use the following command to create the .mo files for each
# locale. This is done when the project is built.
#
# msgfmt po/en.po -o build/share/locale/en/LC_MESSAGES/bauble.mo

# Update the translations after a new message template is created
#find ./po -name \*.po -exec msgmerge -U {} messages.pot \;

