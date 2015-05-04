#!/bin/bash

sudo apt-get -y python-gtk2 git virtualenvwrapper
cat <<EOF >> ~/.profile
export WORKON_HOME=$HOME/.virtualenvs>> ~/.profile
export PROJECT_HOME=$HOME/Devel
source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
EOF
. ~/.profile
mkdir -p ~/Local/github/mfrasca
cd ~/Local/github/mfrasca
git clone https://github.com/mfrasca/bauble.classic
mkvirtualenv bacl --system-site-packages
workon bacl
python setup.py build
python setup.py install
mkdir ~/bin
cat <<EOF > ~/bin/bauble
#!/bin/bash

GITHOME=$HOME/Local/github/mfrasca/bauble.classic/

source /usr/local/bin/virtualenvwrapper.sh
workon bacl

while getopts u f
do
  case $f in
    u)  cd $GITHOME
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
