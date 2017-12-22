===========================================
Building a Windows executable and installer
===========================================

For building a Windows installer or executable you will need an installation of 
Windows.  The methods described here has been used successfully on Windows 7, 
8 and 10.  Windows Vista should also work but has not been tested.


.. admonition:: py2exe will not work with eggs
   :class: note

   Building a windows executable with py2exe requires packages **not** be 
   installed as eggs.  There are several methods to accomplish this, including:

   - Using pip to install.  The easiest method is to install into a virtual 
     environment that doesn't currently have any modules installed as eggs 
     using ``pip install .`` as descibed below.  If you do wish to install over 
     the top of an install with eggs (e.g. the environment created by 
     ``devinstall.bat``  ) you can try ``pip install -I .`` but your mileage 
     may vary. 

   - By adding::

       [easy_install]
       zip_ok = False

     to setup.cfg (or similarly ``zip_safe = False`` to ``setuptools.setup()`` 
     in ``setup.py``) you can use ``python setup.py install`` but you will need 
     to download and install `Microsoft Visual C++ Compiler for Python 2.7 
     <http://aka.ms/vcpython27>`_ to get any of the C extensions and will need 
     a fresh virtual environment with no dependent packages installed as eggs.


#. Download and install git, Python 2.7 and PyGTK external dependencies as 
   outlined in the installation instructions.  You can use the direct links 
   provided here (`git <Direct link to download git_>`_, `Python <Direct link 
   to download Python_>`_, `PyGTK <Direct link to download PyGTK_>`_) but 
   remember to select the option to put Python in the PATH and install **all** 
   components of PyGTK. (Wait for Python install to complete before installing 
   PyGTK)

#. If you wish to produce an installer download and install `NSIS v3 
   <http://nsis.sourceforge.net/Download>`_.  

#. A **reboot** is recommended.

#. Clone ghini.desktop to wherever you want to keep it (replace 
   ``<path-to-keep-ghini>`` with the path of your choice, e.g. ``Downloads``) 
   and checkout the branch you wish to build (``ghini-1.0`` is recommended as 
   used in the example).  To do this, open a command prompt and type these 
   commands::

      cd <path-to-keep-ghini>
      git clone https://github.com/Ghini/ghini.desktop.git
      cd ghini.desktop
      git checkout ghini-1.0

   .. admonition:: shortcut using build_win.bat
      :class: note

      A batch file is available that can complete these last few steps.  To use 
      it use this command::

         scripts\build_win.bat

      ``build_win.bat`` accepts 2 arguments:

      #. ``/e`` will produce an executable only, skipping the extra step of 
         building an installer, and will copy ``win_gtk.bat`` into place.

      #. A path to the location for the virtual environment to use. (defaults 
         to ``"%HOMEDRIVE%%HOMEPATH%"\.virtualenvs\ghi2exe``)

      e.g. to produce an executable only and use a virtual environment in 
      a folder beside where you have ghini.desktop you could execute 
      ``scripts\build_win.bat /e ..\ghi2exe``

#. Install virtualenv, create a virtual environment and activate it.  With only 
   Python 2.7 on your system (where ``<path-to-venv>`` is the path to where you 
   wish to keep the virtual environment) use::

      pip install virtualenv
      virtualenv --system-site-packages <path-to-venv>
      call <path-to-venv>\Scripts\activate.bat

   On systems where Python 3 is also installed you may need to either call pip 
   and virtualenv with absolute paths e.g.  ``C:\Python27\Scripts\pip`` or use 
   the Python launcher e.g. ``py -2.7 -m pip`` (run ``python --version`` first 
   to check.  If you get anything other than version 2.7 you'll need to use one 
   of these methods.)

#. Install dependencies and ghini.desktop into the virtual environment::

      pip install psycopg2 Pygments py2exe_py2
      pip install .

#. Build the executable::

      python setup.py py2exe

   The ``dist`` folder will now contain a full working copy of the software in 
   a frozen, self contained state, that can be transferred however you like and 
   will work in place.  (e.g. placed on a USB flash drive for demonstration 
   purposes or copied manually to ``C:\Program Files`` with a shortcut created 
   on the desktop).  To start ghini.desktop double click ``ghini.exe`` in 
   explorer (or create a shortcut to it). If you have issues with the UI not 
   displaying correctly you need to run the script ``win_gtk.bat`` from the 
   ``dist`` folder to set up paths to the GTK components correctly.  (Running 
   ``build_win /e`` will place this script in the dist folder for you or you 
   can copy it from the ``scripts`` folder yourself.)  You will only need to 
   run this once each time the location of the folder changes.  Thereafter 
   ``ghini.exe`` will run as expected.

#. Build the installer::

      python setup.py nsis

   This should leave a file named ``ghini.desktop-<version>-setup.exe`` in the 
   ``scripts`` folder.  This is your Windows installer.


.. admonition:: about the installer
   :class: note

   -  Capable of single user or global installs.

   -  At this point in time ghini.desktop installed this way will not check
      or or notify you of any updated version.  You will need to check 
      yourself.

   -  Capable of downloading and installing optional extra components:

      -  Apache FOP - If you want to use xslt report templates install FOP.  
         FOP requires Java Runtime. If you do not currently have it installed 
         the installer will let you know and offer to open the Oracle web site 
         for you to download and install it from.

      -  MS Visual C runtime - You most likely don't need this but if you have 
         any trouble getting ghini.desktop to run try installing the MS Visual 
         C runtime (e.g. rerun the installer and select this component only).

   -  Can be run silently from the commandline (e.g. for remote deployment) 
      with the following arguments:

      - ``/S`` for silent;

      - ``/AllUser`` (when run as administrator) or ``/CurrentUser``

      - ``/C=[gFC]`` to specify components where:

            ``g`` = Deselect the main ghini.desktop component (useful for 
            adding optional component after an initial install)

            ``F`` = select Apache FOP

            ``C`` = select MS Visual C runtime


.. _Direct link to download git: https://github.com/git-for-windows/git/releases/download/v2.13.3.windows.1/Git-2.13.3-32-bit.exe
.. _Direct link to download Python: https://www.python.org/ftp/python/2.7.12/python-2.7.12.msi
.. _Direct link to download lxml: https://pypi.python.org/packages/2.7/l/lxml/lxml-3.6.0.win32-py2.7.exe
.. _Direct link to download PyGTK: http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/pygtk-all-in-one-2.24.2.win32-py2.7.msi
.. _Direct link to download psycopg2: http://www.stickpeople.com/projects/python/win-psycopg/2.6.1/psycopg2-2.6.1.win32-py2.7-pg9.4.4-release.exe

