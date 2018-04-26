@echo off
call "%HOMEDRIVE%%HOMEPATH%"\.virtualenvs\ghide\Scripts\activate.bat
cd "%HOMEDRIVE%%HOMEPATH%"\Local\github\Ghini\ghini.desktop
git pull > ghini-update.log
python setup.py build | scripts\tee.bat ghini-update.log 1
python setup.py install | scripts\tee.bat ghini-update.log 1
