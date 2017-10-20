@echo off

IF NOT EXIST %HOMEDRIVE%%HOMEPATH%\.virtualenvs\ghi2exe\Scripts\activate.bat (
  ECHO creating an isolated virtual environment to build in
  pip install virtualenv
  virtualenv --system-site-packages %HOMEDRIVE%%HOMEPATH%\.virtualenvs\ghi2exe
)

IF "%VIRTUAL_ENV%"=="" (
  ECHO Activating virtual environment to build in.
  call %HOMEDRIVE%%HOMEPATH%\.virtualenvs\ghi2exe\Scripts\activate.bat
) else (
  ECHO Currently using virtual environment: "%VIRTUAL_ENV%"
  IF NOT "%VIRTUAL_ENV%"=="%HOMEDRIVE%%HOMEPATH%\.virtualenvs\ghi2exe" (
    ECHO deactivating previous virtual environment and activating one to build in
    deactivate
    call %HOMEDRIVE%%HOMEPATH%\.virtualenvs\ghi2exe\Scripts\activate.bat
  )
)

ECHO Installing dependancies
pip install py2exe_py2
pip install psycopg2
pip install Pygments

ECHO cleaning up
python setup.py clean

ECHO installing dependencies - without eggs
pip install .

ECHO building frozen distribution
python setup.py py2exe

REM Freeze only?
if "%1"=="/f" GOTO :EOF

ECHO building NSIS installer
python setup.py nsis
