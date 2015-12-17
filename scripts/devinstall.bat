@echo off
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
echo NET SESSION >nul 2>&1
echo IF %ERRORLEVEL% EQU 0 (
echo  mkdir "%AUSTARTMENU%\Programs\Bauble"
echo  copy "%HOMEDRIVE%%HOMEPATH%"\Local\github\Bauble\bauble.classic\scripts\bauble.lnk "%AUSTARTMENU%\Programs\Bauble"
echo ) else (
echo )
) > devinstall-finalize.bat

ECHO please run devinstall-finalize.bat as administrator.
pause
