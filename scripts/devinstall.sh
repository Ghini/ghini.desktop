#!/bin/bash

PROBLEMS=''
if ! msgfmt --version >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS gettext"
fi
if ! python -c 'import gtk' >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS python-gtk2"
fi
if ! git help >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS git"
fi
if ! virtualenv --help >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS python-virtualenv"
fi
if ! xslt-config --help >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS libxslt1-dev"
fi
PYTHONHCOUNT=$(find /usr/include/python* /usr/local/include/python* -name Python.h 2>/dev/null | wc -l)
if [ "$PYTHONHCOUNT" = "0" ]; then
    PROBLEMS="$PROBLEMS python-all-dev"
fi
SETUPTOOLS=$(pip show setuptools | grep Version | cut -f2 -d:)
EXPRESSION=$(echo "$SETUPTOOLS" | cut -d- -f1 | cut -d. -f1-2)" <= 0.6"
if [ $(echo $EXPRESSION | bc) -eq 1 ]; then
    echo "your setuptools are really old. expect trouble."
fi

if [ "$PROBLEMS" != "" ]; then
    echo please first solve the following dependencies:
    echo '     (package names are ubuntu/debian, YMMV).'
    echo $PROBLEMS
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
virtualenv $HOME/.virtualenvs/ghide11 --system-site-packages
find $HOME/.virtualenvs/ghide11 -name "*.pyc" -or -name "*.pth" -execdir rm {} \;
mkdir -p $HOME/.virtualenvs/ghide11/share
mkdir -p $HOME/.bauble
source $HOME/.virtualenvs/ghide11/bin/activate

pip install setuptools pip --upgrade

python setup.py build
python setup.py install
mkdir -p $HOME/bin 2>/dev/null
cat <<EOF > $HOME/bin/ghini11
#!/bin/bash

GITHOME=$HOME/Local/github/Ghini/ghini.desktop/
source \$HOME/.virtualenvs/ghide11/bin/activate

BUILDANDEND=0
while getopts us: f
do
  case \$f in
    u)  cd \$GITHOME
        BUILDANDEND=1;;
    s)  cd \$GITHOME
        git checkout ghini-\$OPTARG || exit 1
        BUILDANDEND=1;;
  esac
done

if [ "\$BUILDANDEND" == "1" ]
then
    git pull
    python setup.py build
    python setup.py install
    exit 1
fi

ghini
EOF
chmod +x $HOME/bin/ghini11

echo your local installation is now complete.
echo enter your password to make Ghini available to other users.

sudo addgroup ghini 2>/dev/null 
sudo usermod -a -G ghini $(whoami)
chmod -R g-w+rX,o-rwx $HOME/.virtualenvs/ghide11
sudo chgrp -R ghini $HOME/.virtualenvs/ghide11
cat <<EOF | sudo tee /usr/local/bin/ghini11 > /dev/null
#!/bin/bash
source $HOME/.virtualenvs/ghide11/bin/activate
$HOME/.virtualenvs/ghide11/bin/ghini
EOF
sudo chmod +x /usr/local/bin/ghini11
