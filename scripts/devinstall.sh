#!/bin/bash

#echo missing in vanilla ubuntu - to run 'pip install bauble'
#echo libxslt1-dev python-all-dev gettext

while true
do

    PROBLEMS=''
    if ! msgfmt --version >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS gettext"
    fi
    if ! python3 --version >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS python3-minimal"
    fi
    if ! python3 -c 'import gi' >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS python3-gi"
    fi
    if ! python3 -c 'import gi; gi.require_version("Clutter", "1.0"); gi.require_version("GtkClutter", "1.0"); from gi.repository import Clutter, GtkClutter; ' >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS gir1.2-gtkclutter "
    fi
    if ! python3 -c 'import gi; gi.require_version("Clutter", "1.0"); gi.require_version("GtkClutter", "1.0"); from gi.repository import Clutter, GtkClutter; gi.require_version("Champlain", "0.12"); from gi.repository import GtkChamplain; GtkClutter.init([]); from gi.repository import Champlain' >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS gir1.2-gtkchamplain-0.12 "
    fi
    if ! python3 -c 'import lxml' >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS python3-lxml"
    fi
    if ! git help >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS git"
    fi
    if ! virtualenv --help >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS virtualenv"
    fi
    if ! xslt-config --help >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS libxslt1-dev"
    fi
    if ! pkg-config --help >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS pkg-config"
    fi
    if ! pkg-config --cflags jpeg --help >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS libjpeg-dev"
    fi
    if ! gcc --version >/dev/null 2>&1; then
        PROBLEMS="$PROBLEMS build-essential"
    fi
    PYTHONHCOUNT=$(find /usr/include/python3* /usr/local/include/python3* -name Python.h 2>/dev/null | wc -l)
    if [ "$PYTHONHCOUNT" = "0" ]; then
        PROBLEMS="$PROBLEMS libpython3-all-dev"
    fi

    # forget password, please.
    sudo -k

    if [ "$PROBLEMS" == "" ]
    then
        break;
    else
        echo 'Guessing package names, if you get in a loop, please double check.'
        echo 'You need to solve the following dependencies:'
        echo '------------------------------------------------------------------'
        echo $PROBLEMS
        echo '------------------------------------------------------------------'
        echo 'Then restart the devinstall.sh script'
        if [ -x /usr/bin/apt-get ]; then
            echo
            echo 'you are on a debian-like system, I should know how to install'
            echo $PROBLEMS
            sudo apt-get -y install $PROBLEMS
            echo -n 'press <ENTER> to re-run devinstall.sh, or Ctrl-C to stop'
            read
        fi
    fi
done

if [ -d $HOME/Local/github/Ghini/ghini.desktop ]
then
    echo "ghini checkout already in place"
    cd $HOME/Local/github/Ghini/ghini.desktop
else
    mkdir -p $HOME/Local/github/Ghini >/dev/null 2>&1
    cd $HOME/Local/github/Ghini
    git clone https://github.com/Ghini/ghini.desktop
    cd ghini.desktop
fi

if [ $# -ne 0 ]
then
    git checkout ghini-$1
else
    git checkout ghini-3.1
fi

mkdir -p $HOME/.virtualenvs
virtualenv --python python3 $HOME/.virtualenvs/ghide --system-site-packages
find $HOME/.virtualenvs/ghide -name "*.pyc" -or -name "*.pth" -execdir rm {} \;
mkdir -p $HOME/.virtualenvs/ghide/share
mkdir -p $HOME/.ghini
. $HOME/.virtualenvs/ghide/bin/activate

if [ ! -z $PG ]
then
    echo 'installing postgresql adapter'
    pip install psycopg2 ;
fi

if [ ! -z $MYSQL ]
then
    echo 'installing mysql adapter'
    pip install mysqlclient ;    
fi

python setup.py build
python setup.py install
mkdir -p $HOME/bin 2>/dev/null
cat <<EOF > $HOME/bin/ghini
#!/bin/bash

GITHOME=$HOME/Local/github/Ghini/ghini.desktop/
. \$HOME/.virtualenvs/ghide/bin/activate

while getopts us:mp f
do
  case \$f in
    u)  cd \$GITHOME
        BUILD=1
        END=1
        ;;
    s)  cd \$GITHOME
        git checkout ghini-\$OPTARG || exit 1
        BUILD=1
        END=1
        ;;
    m)  pip install mysqlclient
        END=1
        ;;
    p)  pip install psycopg2
        END=1
        ;;
  esac
done

if [ ! -z "\$BUILD" ]
then
    git pull
    python setup.py build
    python setup.py install
fi

if [ ! -z "\$END" ]
then
    exit 1
fi

ghini
EOF
chmod +x $HOME/bin/ghini

echo your local installation is now complete.
echo enter your password to make Ghini available to other users.

sudo groupadd ghini 2>/dev/null 
sudo usermod -a -G ghini $(whoami)
chmod -R g-w+rX,o-rwx $HOME/.virtualenvs/ghide
sudo chgrp -R ghini $HOME/.virtualenvs/ghide
cat <<EOF | sudo tee /usr/local/bin/ghini > /dev/null
#!/bin/bash
. $HOME/.virtualenvs/ghide/bin/activate
$HOME/.virtualenvs/ghide/bin/ghini
EOF
sudo chmod +x /usr/local/bin/ghini

sudo mkdir -p /usr/local/share/applications/ >/dev/null 2>&1
cat <<EOF | sudo tee /usr/local/share/applications/ghini.desktop > /dev/null
#!/bin/bash
[Desktop Entry]
Type=Application
Name=Ghini Desktop
Version=3.1
GenericName=Biodiversity Manager
Icon=$HOME/.virtualenvs/ghide/share/icons/hicolor/scalable/apps/ghini.svg
TryExec=/usr/local/bin/ghini
Exec=/usr/local/bin/ghini
Terminal=false
StartupNotify=false
Categories=Qt;Education;Science;Geography;
Keywords=botany;botanic;
EOF
