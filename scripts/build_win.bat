@ECHO off
SETLOCAL

REM process command line arguments (/e produces exe only not installer,
REM only other argument proccessed must be a pathname to a virtualenv)
:Loop
IF [%1]==[] GOTO Continue
IF "%1"=="/e" (
    SET EXEONLY=y
) ELSE (
    SET CUSTOMVENV="%~f1"
)
SHIFT
GOTO Loop
:Continue

FOR /F %%i in ('git rev-parse --abbrev-ref HEAD') DO CHECKOUT=%%i

IF defined EXEONLY ECHO build exe only

IF defined CUSTOMVENV (
    ECHO using custom virtual environment %CUSTOMVENV%
) ELSE (
    SET CUSTOMVENV="%HOMEDRIVE%%HOMEPATH%\.virtualenvs\%CHECKOUT%-exe"
)

IF NOT EXIST %CUSTOMVENV%\Scripts\activate.bat (
    ECHO creating build environment
    REM STEP 1 - install virtualenv and create a virtual environment
    C:\Python27\Scripts\pip install virtualenv
    C:\Python27\Scripts\virtualenv --system-site-packages %CUSTOMVENV%
)

IF "%VIRTUAL_ENV%"=="" (
    ECHO Activating build environment
    REM STEP 2 - activate the virtual environment
    call %CUSTOMVENV%\Scripts\activate.bat
) ELSE (
    ECHO Current virtual environment: "%VIRTUAL_ENV%"
    IF NOT "%VIRTUAL_ENV%"==%CUSTOMVENV% (
        ECHO deactivating current virtual environment and activating build environment
        call deactivate
        call %CUSTOMVENV%\Scripts\activate.bat
    )
)


ECHO Installing dependencies
REM STEP 3 - Install dependencies into the virtual environment
"%VIRTUAL_ENV%"\Scripts\Python.exe -m pip install --upgrade pip
pip install py2exe_py2
pip install psycopg2
pip install Pygments

ECHO cleaning up
REM STEP 4 - clean up any previous builds
del /f /s /q ghini-runtime 1>nul
mkdir dist 2>nul
forfiles /P "%VIRTUAL_ENV%"\Lib\site-packages\ /M ghini.desktop-*.egg-info /C^
    "cmd /c if @ISDIR==TRUE rmdir /s /q @PATH && echo removing @PATH" 2>NUL

ECHO installing without eggs
REM STEP 5 - install ghini.desktop and its dependencies into the virtual environment
pip install .

ECHO building executable
REM STEP 6 - build the executable
python setup.py py2exe

REM executable only?
IF defined EXEONLY GOTO Skip_NSIS

ECHO building NSIS installer
REM STEP 7 - build the installer
mkdir dist 2>nul
python setup.py nsis

:Skip_NSIS
copy scripts\win_gtk.bat ghini-runtime

ENDLOCAL
