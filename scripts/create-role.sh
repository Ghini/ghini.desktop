#!/bin/bash

usage() {
    cat << EOF 1>&2
$0 - bash helper for creating ghini.desktop PostgreSQL users
Usage: $0 [-d <database>] [-u <admin_account>] <username> <password>
EOF
    exit 1;
}

DATABASE=bauble
ADMIN_ACCOUNT=bauble

while getopts "d:u:p:" o; do
    case "${o}" in
        d)
            DATABASE=${OPTARG}
            ;;
        u)
            ADMIN_ACCOUNT=${OPTARG}
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${DATABASE}" ] || [ -z "${ADMIN_ACCOUNT}" ]; then
    usage
fi

USER=$1
PASSWD=$2
shift 2

cat <<EOF | psql ${DATABASE} -U ${ADMIN_ACCOUNT} $*
create role $USER with login password '$PASSWD';
alter role $USER with login password '$PASSWD';
grant all privileges on all tables in schema public to $USER;
grant all privileges on all sequences in schema public to $USER;
grant all privileges on all functions in schema public to $USER;
EOF
