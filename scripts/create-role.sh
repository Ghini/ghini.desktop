#!/bin/bash

USER=$1
PASSWD=$2
shift 2

cat <<EOF | psql bauble -U bauble $@
create role $USER with login encrypted password '$PASSWD';
grant all privileges on all tables in schema public to $USER;
grant all privileges on all sequences in schema public to $USER;
grant all privileges on all functions in schema public to $USER;
EOF
