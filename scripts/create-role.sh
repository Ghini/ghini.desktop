#!/bin/bash

USER=$1
PASSWD=$2

cat <<EOF | psql bauble -U bauble
create role $1 with login encrypted password '$2';
grant all privileges on all tables in schema public to $1;
grant all privileges on all sequences in schema public to $1;
grant all privileges on all functions in schema public to $1;
EOF
