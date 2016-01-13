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
set CHECKOUT=bauble-%1
GOTO CONTINUE

:DEFAULTCHOICE
set CHECKOUT=bauble-1.0

:CONTINUE

ECHO going to install %CHECKOUT%
cd "%HOMEDRIVE%%HOMEPATH%"

ECHO installing dependencies
pip install virtualenv 2>NUL
virtualenv --system-site-packages .virtualenvs\bacl

ECHO clearing previous checkouts
for /F "delims=" %%i in (
  'dir /b .virtualenvs\bacl\Lib\site-packages\bauble-*egg'
) do (
  rmdir ".virtualenvs\bacl\Lib\site-packages\""%%i" /s/q
)

ECHO going to checkout %CHECKOUT%
call .virtualenvs\bacl\Scripts\activate.bat
mkdir Local\github\Bauble 2>NUL
cd Local\github\Bauble
git clone https://github.com/Bauble/bauble.classic.git
cd bauble.classic
git checkout %CHECKOUT%

ECHO going to build and install
python setup.py build
python setup.py install
mkdir "%APPDATA%\Bauble" 2>NUL
cd "%HOMEPATH%"

ECHO create the globalizing script
IF DEFINED PUBLIC (SET AUDESKTOP=%PUBLIC%\Desktop) & (SET AUSTARTMENU=%PROGRAMDATA%\Microsoft\Windows\Start Menu) ELSE (SET AUDESKTOP=%ALLUSERSPROFILE%\Desktop) & (SET AUSTARTMENU=%ALLUSERSPROFILE%\Start Menu)
(
echo @echo off
echo mkdir "%AUSTARTMENU%\Programs\Bauble"
echo copy "%HOMEDRIVE%%HOMEPATH%"\Local\github\Bauble\bauble.classic\scripts\bauble.lnk "%AUSTARTMENU%\Programs\Bauble"
) > devinstall-finalize.bat

ECHO please run devinstall-finalize.bat as administrator.
pause
