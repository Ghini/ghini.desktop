#!/bin/sh
#export PYTHONPATH=`dirname $0`
SCRIPT_PATH=`dirname $0`/scripts/bauble
PYTHONPATH=`dirname $0` python $SCRIPT_PATH
PYTHONPATH=`dirname $0` exec python $SCRIPT_PATH
