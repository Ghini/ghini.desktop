@echo off
call "%HOMEDRIVE%%HOMEPATH%"\.virtualenvs\ghide\Scripts\activate.bat

rem get the short name of python's executable in the virtual env.
rem this is the python we expect to load.
for %%i in ("%HOMEDRIVE%%HOMEPATH%\.virtualenvs\ghide\Scripts\python.exe") do (
  set SVEP=%%~fsi
)
for %%i in (python.exe) do (
  if not %%~$PATH:i==%SVEP% (
    echo please rebuild your virtual environment.
    exit /b
  ) else (
    echo virtual environment looks fine, proceeding...
  )
)

cd "%HOMEDRIVE%%HOMEPATH%"\Local\github\Ghini\ghini.desktop
git pull | scripts\tee.bat ghini-update.log
python setup.py build | scripts\tee.bat ghini-update.log 1
python setup.py install | scripts\tee.bat ghini-update.log 1
