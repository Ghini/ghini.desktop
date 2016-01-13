#!/bin/sh
#export PYTHONPATH=`dirname $0`
SCRIPT_PATH=`dirname $0`/scripts/bauble
# TODO: for some reason this doesn't really load the version of bauble
# in PYTHONPATH, it will load the installed (/usr/lib/pythonX.Y)
# version first....why?
PYTHONPATH=`dirname $0` exec python $SCRIPT_PATH
