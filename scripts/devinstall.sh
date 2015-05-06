#!/bin/bash

if [ -d ~/Local/github/Bauble ]
then
  echo "bauble checkout already in place"
  exit 1
fi

sudo apt-get install -y python-gtk2 git virtualenvwrapper
cat <<EOF >> ~/.profile
export WORKON_HOME=$HOME/.virtualenvs
export PROJECT_HOME=$HOME/Devel
source $(which virtualenvwrapper.sh)
EOF
. ~/.profile
mkdir -p ~/Local/github/Bauble
cd ~/Local/github/Bauble
git clone https://github.com/Bauble/bauble.classic
cd bauble.classic
if [ $# -ne 0 ]
then
  git checkout bauble-$1
fi
mkvirtualenv bacl --system-site-packages
workon bacl
python setup.py build
python setup.py install
mkdir ~/bin 2>/dev/null
cat <<EOF > ~/bin/bauble
#!/bin/bash

GITHOME=$HOME/Local/github/Bauble/bauble.classic/

source /usr/local/bin/virtualenvwrapper.sh
workon bacl

while getopts us: f
do
  case \$f in
    u)  cd \$GITHOME
	git pull
	python setup.py build
	python setup.py install
	exit 1;;
    s)  cd \$GITHOME
	git checkout bauble-$OPTARG
        git pull
	python setup.py build
	python setup.py install
	exit 1;;
  esac
done

bauble
deactivate
EOF
chmod +x ~/bin/bauble
