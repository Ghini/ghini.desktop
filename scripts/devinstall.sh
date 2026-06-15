#!/bin/bash
set -euo pipefail

GITHOME="$HOME/Local/github.com/Ghini/ghini.desktop"

# ── 1. System dependency checks ──────────────────────────────────────────────

while true; do
    MISSING=''

    if ! sudo --version >/dev/null 2>&1; then
        MISSING="$MISSING sudo"
    fi
    if ! msgfmt --version >/dev/null 2>&1; then
        MISSING="$MISSING gettext"
    fi
    if ! python3 --version >/dev/null 2>&1; then
        MISSING="$MISSING python3-minimal"
    fi
    if ! python3 -c 'import gi' >/dev/null 2>&1; then
        MISSING="$MISSING python3-gi"
    fi
    if ! python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
        MISSING="$MISSING gir1.2-gtk-3.0"
    fi
    if ! python3 -c 'import cairo' >/dev/null 2>&1; then
        MISSING="$MISSING python3-gi-cairo"
    fi
    if ! python3 -c 'import gi; gi.require_version("Clutter", "1.0"); from gi.repository import Clutter' >/dev/null 2>&1; then
        MISSING="$MISSING gir1.2-clutter-1.0"
    fi
    if ! python3 -c 'import gi; gi.require_version("GtkClutter", "1.0"); from gi.repository import GtkClutter' >/dev/null 2>&1; then
        MISSING="$MISSING gir1.2-gtkclutter-1.0"
    fi
    if ! python3 -c 'import gi; gi.require_version("Champlain", "0.12"); from gi.repository import Champlain' >/dev/null 2>&1; then
        MISSING="$MISSING gir1.2-champlain-0.12"
    fi
    if ! python3 -c 'import gi; gi.require_version("GtkChamplain", "0.12"); from gi.repository import GtkChamplain' >/dev/null 2>&1; then
        MISSING="$MISSING gir1.2-gtkchamplain-0.12"
    fi
    if ! python3 -c 'import lxml' >/dev/null 2>&1; then
        MISSING="$MISSING python3-lxml"
    fi
    if ! git help >/dev/null 2>&1; then
        MISSING="$MISSING git"
    fi
    if ! pkg-config --version >/dev/null 2>&1; then
        MISSING="$MISSING pkg-config"
    fi
    if ! pkg-config --cflags cairo >/dev/null 2>&1; then
        MISSING="$MISSING libcairo2-dev"
    fi
    if ! pkg-config --cflags libpq >/dev/null 2>&1; then
        MISSING="$MISSING libpq-dev"
    fi
    if ! pkg-config --cflags libjpeg >/dev/null 2>&1; then
        MISSING="$MISSING libjpeg-dev"
    fi
    if ! pkg-config --cflags libxslt >/dev/null 2>&1; then
        MISSING="$MISSING libxslt1-dev"
    fi
    if ! gcc --version >/dev/null 2>&1; then
        MISSING="$MISSING build-essential"
    fi
    if ! python3 -c 'import venv' >/dev/null 2>&1; then
        MISSING="$MISSING python3-venv"
    fi
    PYTHONHCOUNT=$(find /usr/include/python3* /usr/local/include/python3* -name Python.h 2>/dev/null | wc -l)
    if [ "$PYTHONHCOUNT" = "0" ]; then
        MISSING="$MISSING python3-dev"
    fi

    sudo -k

    if [ "$MISSING" = "" ]; then
        break
    else
        echo 'Guessing package names, if you get in a loop, please double check.'
        echo 'In Debian terms, you need to solve the following dependencies:'
        echo '------------------------------------------------------------------'
        echo $MISSING
        echo '------------------------------------------------------------------'
        echo 'Then restart the devinstall.sh script'
        echo
        if [ -x /usr/bin/apt-get ]; then
            echo 'you are on a debian-like system, I should know how to proceed'
            sudo apt-get -y install $MISSING
        elif [ -x /usr/bin/pacman ]; then
            echo 'your system looks like Archlinux, I give it a try'
            MISSING=$(echo $MISSING |
                sed -e 's/build-essential/gcc make libc-dev/' |
                sed -e 's/python3-venv/python-venv/' |
                sed -e 's/python3-lxml/python-lxml/' |
                sed -e 's/libjpeg-dev/libjpeg-turbo/' |
                sed -e 's/libcairo2-dev/cairo/' |
                sed -e 's/libpq-dev/postgresql-libs/' |
                sed -e 's/libxslt1-dev/libxslt/' |
                sed -e 's/python3-gi/python-gobject/' |
                sed -e 's/python3-gi-cairo/python-gobject/' |
                sed -e 's/gir1.2-gtk-3.0/gtk3/' |
                sed -e 's/gir1.2-clutter-1.0/clutter/' |
                sed -e 's/gir1.2-gtkclutter-1.0/clutter-gtk/' |
                sed -e 's/gir1.2-champlain-0.12/libchamplain/' |
                sed -e 's/gir1.2-gtkchamplain-0.12/libchamplain/' |
                sed -e 's/python3-dev/python-dev/')
            sudo pacman -S $MISSING
        elif [ -x /usr/bin/rpm ]; then
            echo 'your system looks like RedHat.'
            exit 1
        else
            echo 'so sorry, I have no clue about your system.'
            exit 1
        fi
        echo -n 'press <ENTER> to re-run devinstall.sh, or Ctrl-C to stop'
        read
    fi
done

# ── 2. Clone or update repository ────────────────────────────────────────────

if [ -d "$GITHOME" ]; then
    echo "ghini checkout already in place"
else
    mkdir -p "$(dirname "$GITHOME")"
    git clone https://github.com/Ghini/ghini.desktop "$GITHOME"
fi
cd "$GITHOME"

# Choose branch: prefer stable release, fall back to dev
if [ $# -ne 0 ]; then
    VERSION=$1
    LINE=ghini-$1
else
    VERSION=3.1
    # Use stable branch if it exists remotely, otherwise dev
    if git ls-remote --exit-code origin ghini-3.1 >/dev/null 2>&1; then
        LINE=ghini-3.1
    else
        LINE=ghini-3.1-dev
    fi
fi

git checkout "$LINE"

# ── 3. Install WFO intermediate certificate ───────────────────────────────────

if [ ! -f /usr/local/share/ca-certificates/network-solutions-rsa-ov-ssl-ca-3.crt ]; then
    echo 'Installing WFO intermediate certificate...'
    sudo cp docker/certs/network-solutions-rsa-ov-ssl-ca-3.crt \
        /usr/local/share/ca-certificates/
    sudo update-ca-certificates
fi

# ── 4. Create virtualenv and install ─────────────────────────────────────────

mkdir -p "$HOME/.virtualenvs"
python3 -m venv "$HOME/.virtualenvs/$LINE" --system-site-packages
find "$HOME/.virtualenvs/$LINE" -name "*.pyc" -execdir rm {} \;
mkdir -p "$HOME/.virtualenvs/$LINE/share"
mkdir -p "$HOME/.ghini"
source "$HOME/.virtualenvs/$LINE/bin/activate"

if [ -n "${PG:-}" ]; then
    echo 'installing postgresql adapter'
    pip install psycopg2
fi

if [ -n "${MYSQL:-}" ]; then
    echo 'installing mysql adapter'
    pip install mysqlclient
fi

pip install -e ".[test]"

# ── 5. Generate launcher script ───────────────────────────────────────────────

mkdir -p "$HOME/bin"
cat > "$HOME/bin/ghini" <<EOF
#!/bin/bash

GITHOME=$GITHOME
LINE=$LINE
. \$HOME/.virtualenvs/\$LINE/bin/activate
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

while getopts us:mp f; do
  case \$f in
    u)  cd \$GITHOME
        git pull --ff-only
        pip install -e ".[test]"
        exit 0 ;;
    s)  [[ -n "\${OPTARG:-}" ]] || { echo "usage: ghini -s VERSION" >&2; exit 2; }
        cd \$GITHOME
        git checkout "ghini-\$OPTARG" || exit 1
        pip install -e ".[test]"
        exit 0 ;;
    m)  pip install mysqlclient; exit 0 ;;
    p)  pip install psycopg2; exit 0 ;;
  esac
done

exec python "\$GITHOME/scripts/ghini" "\$@"
EOF
chmod +x "$HOME/bin/ghini"

# ── 6. System-wide launcher and desktop entry ─────────────────────────────────

echo 'your local installation is now complete.'
echo 'enter your password to make Ghini available to other users.'

sudo groupadd ghini 2>/dev/null || true
sudo usermod -a -G ghini "$(whoami)"
chmod -R g-w+rX,o-rwx "$HOME/.virtualenvs/$LINE"
sudo chgrp -R ghini "$HOME/.virtualenvs/$LINE"

cat <<EOF | sudo tee /usr/local/bin/ghini > /dev/null
#!/bin/bash
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
. $HOME/.virtualenvs/$LINE/bin/activate
exec python $GITHOME/scripts/ghini "\$@"
EOF
sudo chmod +x /usr/local/bin/ghini

sudo mkdir -p /usr/local/share/applications/
cat <<EOF | sudo tee /usr/local/share/applications/ghini.desktop > /dev/null
[Desktop Entry]
Type=Application
Name=Ghini Desktop
Version=$VERSION
GenericName=Biodiversity Manager
Icon=$HOME/.virtualenvs/$LINE/share/icons/hicolor/scalable/apps/ghini.svg
TryExec=/usr/local/bin/ghini
Exec=/usr/local/bin/ghini
Terminal=false
StartupNotify=false
Categories=Education;Science;Geography;
Keywords=botany;botanic;
EOF
