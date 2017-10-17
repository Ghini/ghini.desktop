@echo off
ECHO sanity check

SET SHOULD_CANCEL=0

python -c "1" 2>NUL
IF %ERRORLEVEL% NEQ 0 (
 ECHO Python not properly installed
 SET SHOULD_CANCEL=1
 goto SKIP_GTK_TEST
)
python -c "import gtk" 2>NUL
IF %ERRORLEVEL% NEQ 0 (
  ECHO PyGtk not properly installed
  SET SHOULD_CANCEL=1
)
:SKIP_GTK_TEST
git --version 2>NUL >NUL
IF %ERRORLEVEL% NEQ 0 (
  ECHO git not properly installed
  SET SHOULD_CANCEL=1
)

IF %SHOULD_CANCEL% NEQ 0 exit /b
ECHO sanity check passed

IF %1.==. GOTO DEFAULTCHOICE
set CHECKOUT=ghini-%1
GOTO CONTINUE

:DEFAULTCHOICE
set CHECKOUT=ghini-1.0-wininstaller

:CONTINUE

ECHO going to install %CHECKOUT%
cd "%HOMEDRIVE%%HOMEPATH%"

ECHO installing dependencies
pip install virtualenv 2>NUL
virtualenv --system-site-packages .virtualenvs\ghi2exe

ECHO clearing previous checkouts
for /F "delims=" %%i in (
  'dir /b .virtualenvs\ghi2exe\Lib\site-packages\bauble-*egg'
) do (
  rmdir ".virtualenvs\ghi2exe\Lib\site-packages\""%%i" /s/q 2>NUL
)

ECHO going to checkout %CHECKOUT%
call .virtualenvs\ghi2exe\Scripts\activate.bat
mkdir Local\github\Ghini 2>NUL
cd Local\github\Ghini
git clone https://github.com/RoDuth/ghini.desktop.git
cd ghini.desktop
git checkout %CHECKOUT%
git pull

ECHO create the program shortcut
pip install pypiwin32 2>NUL
python scripts\mklnk.py

pip install psycopg2
pip install lxml
pip install Pygments
pip install py2exe_py2

ECHO going to build and install
python setup.py build
python setup.py install
mkdir "%APPDATA%\Ghini" 2>NUL
cd "%HOMEPATH%"

ECHO create the globalizing script
IF DEFINED PUBLIC (SET AUDESKTOP=%PUBLIC%\Desktop) & (SET AUSTARTMENU=%PROGRAMDATA%\Microsoft\Windows\Start Menu) ELSE (SET AUDESKTOP=%ALLUSERSPROFILE%\Desktop) & (SET AUSTARTMENU=%ALLUSERSPROFILE%\Start Menu)
(
echo @echo off
echo mkdir "%AUSTARTMENU%\Programs\Ghini"
echo copy "%HOMEDRIVE%%HOMEPATH%"\Local\github\Ghini\ghini.desktop\scripts\ghini.lnk "%AUSTARTMENU%\Programs\Ghini"
) > devinstall-finalize.bat

ECHO please run devinstall-finalize.bat as administrator.
pause
