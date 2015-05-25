#!/bin/bash

PROBLEMS=''
if ! python -c 'import gtk' >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS pygtk"
fi
if ! git help >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS git"
fi
if ! virtualenv --help >/dev/null 2>&1; then
    PROBLEMS="$PROBLEMS virtualenv"
fi

if [ "$PROBLEMS" != "" ]; then
    echo please first solve dependencies.
    echo $PROBLEMS
    exit 1
fi

if [ -d ~/Local/github/Bauble/bauble.classic ]
then
    echo "bauble checkout already in place"
    cd ~/Local/github/Bauble/bauble.classic
else
    mkdir -p ~/Local/github/Bauble >/dev/null 2>&1
    cd ~/Local/github/Bauble
    git clone https://github.com/Bauble/bauble.classic
    cd bauble.classic
fi

if [ $# -ne 0 ]
then
    git checkout bauble-$1
else
    git checkout bauble-1.0
fi

mkdir ~/.virtualenvs >/dev/null 2>&1
virtualenv ~/.virtualenvs/bacl --system-site-packages
source ~/.virtualenvs/bacl/bin/activate

python setup.py build
python setup.py install
mkdir ~/bin 2>/dev/null
cat <<EOF > ~/bin/bauble
#!/bin/bash

GITHOME=$HOME/Local/github/Bauble/bauble.classic/

source ~/.virtualenvs/bacl/bin/activate

while getopts us: f
do
  case \$f in
    u)  cd \$GITHOME
	git pull
	python setup.py build
	python setup.py install
	exit 1;;
    s)  cd \$GITHOME
	git checkout bauble-\$OPTARG
        git pull
	python setup.py build
	python setup.py install
	exit 1;;
  esac
done

bauble
EOF
chmod +x ~/bin/bauble
