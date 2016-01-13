@echo off
call "%HOMEDRIVE%%HOMEPATH%"\.virtualenvs\bacl\Scripts\activate.bat
cd "%HOMEDRIVE%%HOMEPATH%"\Local\github\Bauble\bauble.classic
git pull
python setup.py install
