#!/usr/bin/env bash
set -euo pipefail
VERSION="${1:-3.1}"
LINE="ghini-${VERSION}"

if [[ -d "$HOME/Local/github.com/Ghini/ghini.desktop" ]]; then
  REPO_BASE="$HOME/Local/github.com/Ghini"
elif [[ -d "$HOME/Local/github/Ghini/ghini.desktop" ]]; then
  REPO_BASE="$HOME/Local/github/Ghini"
else
  REPO_BASE="$HOME/Local/github.com/Ghini"
fi
REPO_DIR="$REPO_BASE/ghini.desktop"
VENV_DIR="$HOME/.virtualenvs/$LINE"

check_cmd(){ command -v "$1" >/dev/null 2>&1; }
while true; do
  MISSING=""
  check_cmd msgfmt || MISSING+=" gettext"
  check_cmd python3 || MISSING+=" python3"
  check_cmd git || MISSING+=" git"
  check_cmd pkg-config || MISSING+=" pkg-config"
  check_cmd gcc || MISSING+=" build-essential"
  check_cmd xslt-config || MISSING+=" libxslt1-dev"
  python3 -m venv --help >/dev/null 2>&1 || MISSING+=" python3-venv"
  PYTHONHCOUNT=$(find /usr/include /usr/local/include -type f -path '*/python3*/Python.h' 2>/dev/null | wc -l)
  [[ "$PYTHONHCOUNT" == "0" ]] && MISSING+=" python3-dev"
  sudo -k
  [[ -z "$MISSING" ]] && break
  if [[ -x /usr/bin/apt-get ]]; then
    sudo apt-get update
    sudo apt-get -y install $MISSING
  else
    echo "Missing packages:$MISSING"; exit 1
  fi
done

mkdir -p "$REPO_BASE"
[[ -d "$REPO_DIR/.git" ]] || git clone https://github.com/Ghini/ghini.desktop "$REPO_DIR"
cd "$REPO_DIR"
git fetch --all --tags
git checkout "$LINE"

mkdir -p "$HOME/.virtualenvs" "$HOME/.ghini" "$HOME/bin"
python3 -m venv --system-site-packages "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel

[[ -n "${PG:-}" ]] && python -m pip install psycopg2
[[ -n "${MYSQL:-}" ]] && python -m pip install mysqlclient

python -m pip install \
  "SQLAlchemy==1.2.7" \
  "raven==6.7.0" \
  Pillow \
  lxml \
  "pyqrcode==1.2.1" \
  "mako==1.0.7" \
  "gdata==2.0.18" \
  requests \
  "pyparsing==2.2.0" \
  "python-dateutil==2.7.3"

python setup.py build
python setup.py install --single-version-externally-managed --record /tmp/ghini-install-record.txt

cat > "$HOME/bin/ghini" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail
GITHOME="$REPO_DIR"
VENV="$VENV_DIR"
source "\$VENV/bin/activate"
case "${1:-}" in
  -u)
    cd "\$GITHOME"; git pull --ff-only
    python setup.py build
    python setup.py install --single-version-externally-managed --record /tmp/ghini-install-record.txt
    exit 0 ;;
  -s)
    [[ -n "${2:-}" ]] || { echo "usage: ghini -s VERSION" >&2; exit 2; }
    cd "\$GITHOME"; git checkout "ghini-\$2"
    python setup.py build
    python setup.py install --single-version-externally-managed --record /tmp/ghini-install-record.txt
    exit 0 ;;
  -m) python -m pip install mysqlclient; exit 0 ;;
  -p) python -m pip install psycopg2; exit 0 ;;
esac
exec python "\$GITHOME/scripts/ghini" "\$@"
LAUNCHER
chmod +x "$HOME/bin/ghini"

sudo groupadd ghini 2>/dev/null || true
sudo usermod -a -G ghini "$(whoami)" || true
chmod -R g-w+rX,o-rwx "$VENV_DIR"
sudo chgrp -R ghini "$VENV_DIR" || true

cat <<EOF2 | sudo tee /usr/local/bin/ghini >/dev/null
#!/usr/bin/env bash
exec "$HOME/bin/ghini" "$@"
EOF2
sudo chmod +x /usr/local/bin/ghini

echo "Done. Run: $HOME/bin/ghini"
