@echo off
IF %1.==. GOTO DEFAULTCHOICE
set CHECKOUT=bauble-%1
GOTO CONTINUE

:DEFAULTCHOICE
set CHECKOUT=bauble-1.0

:CONTINUE
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
python setup.py build
python setup.py install
mkdir "%APPDATA%\Bauble"
cd "%HOMEPATH%"
