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

ECHO clearing previous checkouts
for /F "delims=" %%i in (
  'dir /b %VIRTUAL_ENV%\Lib\site-packages\ghini.desktop-*egg'
) do (
  rmdir "%VIRTUAL_ENV%\Lib\site-packages\""%%i" /s/q 2>NUL
)

ECHO Installing dependancies
pip install py2exe_py2
pip install lxml
pip install psycopg2
pip install Pygments

ECHO building and installing ghini.desktop - without eggs
python setup.py build
python setup.py install --old-and-unmanageable

ECHO building frozen distribution
python setup.py py2exe

ECHO building NSIS installer
python setup.py nsis
