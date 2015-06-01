@echo off
cd "%HOMEDRIVE%%HOMEPATH%"
pip install virtualenv 2>NUL
virtualenv --system-site-packages .virtualenvs\bacl
call .virtualenvs\bacl\Scripts\activate.bat
mkdir Local\github\Bauble 2>NUL
cd Local\github\Bauble
git clone https://github.com/Bauble/bauble.classic.git
cd bauble.classic
git checkout bauble-1.0
python setup.py build
python setup.py install
mkdir "%APPDATA%\Bauble"
