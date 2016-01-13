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

if [ -d $HOME/Local/github/Bauble/bauble.classic ]
then
    echo "bauble checkout already in place"
    cd $HOME/Local/github/Bauble/bauble.classic
else
    mkdir -p $HOME/Local/github/Bauble >/dev/null 2>&1
    cd $HOME/Local/github/Bauble
    git clone https://github.com/Bauble/bauble.classic
    cd bauble.classic
fi

if [ $# -ne 0 ]
then
    git checkout bauble-$1
else
    git checkout bauble-1.0
fi

mkdir -p $HOME/.virtualenvs
virtualenv $HOME/.virtualenvs/bacl --system-site-packages
find $HOME/.virtualenvs/bacl -name "*.pyc" -or -name "*.pth" -execdir rm {} \;
mkdir -p $HOME/.virtualenvs/bacl/share
mkdir -p $HOME/.bauble
source $HOME/.virtualenvs/bacl/bin/activate

pip install setuptools pip --upgrade

python setup.py build
python setup.py install
mkdir -p $HOME/bin 2>/dev/null
cat <<EOF > $HOME/bin/bauble
#!/bin/bash

GITHOME=$HOME/Local/github/Bauble/bauble.classic/
source \$HOME/.virtualenvs/bacl/bin/activate

BUILDANDEND=0
while getopts us: f
do
  case \$f in
    u)  cd \$GITHOME
        BUILDANDEND=1;;
    s)  cd \$GITHOME
        git checkout bauble-\$OPTARG || exit 1
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

bauble
EOF
chmod +x $HOME/bin/bauble

echo your local installation is now complete.
echo enter your password to make Bauble available to other users.

sudo addgroup bauble 2>/dev/null 
sudo usermod -a -G bauble $(whoami)
chmod -R g-w+rX,o-rwx $HOME/.virtualenvs/bacl
sudo chgrp -R bauble $HOME/.virtualenvs/bacl
cat <<EOF | sudo tee /usr/local/bin/bauble > /dev/null
#!/bin/bash
source $HOME/.virtualenvs/bacl/bin/activate
$HOME/.virtualenvs/bacl/bin/bauble
EOF
sudo chmod +x /usr/local/bin/bauble
