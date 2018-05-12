#!/bin/bash

#echo missing in vanilla ubuntu - to run 'pip install bauble'
#echo libxslt1-dev python-all-dev gettext

PROBLEMS=''
if ! msgfmt --version >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS gettext"
fi
if ! python -c 'import gtk' >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS python-gtk2"
fi
if ! python -c 'import lxml' >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS python-lxml"
fi
if ! git help >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS git"
fi
if ! virtualenv --help >/dev/null 2>&1; then
    # python-virtualenv is on older ubuntu.
    # virtualenv all other systems.
    PROBLEMS="$PROBLEMS virtualenv python-virtualenv"
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
PYTHONHCOUNT=$(find /usr/include/python* /usr/local/include/python* -name Python.h 2>/dev/null | wc -l)
if [ "$PYTHONHCOUNT" = "0" ]; then
    PROBLEMS="$PROBLEMS python-all-dev"
fi

# forget password, please.
sudo -k

if [ "$PROBLEMS" != "" ]; then
    echo 'please solve the following dependencies:'
    echo '(package names are ubuntu/debian, YMMV.)'
    echo '----------------------------------------'
    echo $PROBLEMS
    echo '----------------------------------------'
    echo 'then restart the devinstall.sh script'
    if [ -x /usr/bin/apt-get ]; then
        echo
        echo you are on a debian-like system, I should know how to install
        echo $PROBLEMS
        sudo apt-get -y install $PROBLEMS
        echo please re-run devinstall.sh
    fi
    exit 1
fi

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
    git checkout ghini-1.0
fi

mkdir -p $HOME/.virtualenvs
virtualenv $HOME/.virtualenvs/ghide --system-site-packages
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
    pip install MySQL-python ;    
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
    m)  pip install MySQL-python
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
Version=1.0
GenericName=Biodiversity Manager
Icon=$HOME/.virtualenvs/ghide/share/icons/hicolor/scalable/apps/ghini.svg
TryExec=/usr/local/bin/ghini
Exec=/usr/local/bin/ghini
Terminal=false
StartupNotify=false
Categories=Qt;Education;Science;Geography;
Keywords=botany;botanic;
EOF
