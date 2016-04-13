@echo off
call "%HOMEDRIVE%%HOMEPATH%"\.virtualenvs\ghide\Scripts\activate.bat
cd "%HOMEDRIVE%%HOMEPATH%"\Local\github\Ghini\ghini.desktop
git pull
python setup.py install
