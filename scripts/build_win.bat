@echo off
SETLOCAL

REM process command line arguments (/e produces exe only not installer,
REM only other argument proccessed must be a pathname to a virtualenv)
:Loop
IF [%1]==[] GOTO Continue
IF "%1"=="/e" (
    set exeonly=y
) ELSE (
    set venv="%~f1"
)
SHIFT
GOTO Loop
:Continue

if defined exeonly ECHO build exe only
if defined venv (
    echo using venv %venv%
) else (
    set venv="%HOMEDRIVE%%HOMEPATH%\.virtualenvs\ghi2exe"
)

IF NOT EXIST %venv%\Scripts\activate.bat (
    ECHO creating build environment
    REM STEP 1 - install virtualenv and create a virtual environment
    C:\Python27\Scripts\pip install virtualenv
    C:\Python27\Scripts\virtualenv --system-site-packages %venv%
)

IF "%VIRTUAL_ENV%"=="" (
    ECHO Activating build environment
    REM STEP 2 - activate the virtual environment
    call %venv%\Scripts\activate.bat
) else (
    ECHO Current virtual environment: "%VIRTUAL_ENV%"
    IF NOT "%VIRTUAL_ENV%"==%venv% (
        ECHO deactivating current virtual environment and activating build environment
        call deactivate
        call %venv%\Scripts\activate.bat
    )
)


ECHO Installing dependencies
REM STEP 3 - Install dependencies into the virtual environment
pip install py2exe_py2
pip install psycopg2
pip install Pygments

ECHO cleaning up
REM STEP 4 - clean up any previous builds
python setup.py clean
forfiles /P "%VIRTUAL_ENV%"\Lib\site-packages\ /M ghini.desktop-*.egg-info /C^
    "cmd /c if @ISDIR==TRUE rmdir /s /q @PATH && echo removing @PATH" 2>NUL

ECHO installing without eggs
REM STEP 5 - install ghini.desktop and it's dependencies into the virtual environment
pip install .

ECHO building executable
REM STEP 6 - build the executable
python setup.py py2exe

REM executable only?
if defined exeonly GOTO SKIP_NSIS

ECHO building NSIS installer
REM STEP 7 - build the installer
python setup.py nsis
GOTO :END

:SKIP_NSIS
copy scripts\win_gtk.bat dist

:END
ENDLOCAL
