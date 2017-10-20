============================
Building a Windows installer
============================

For building a Windows installer you will need an installation of Windows.  The 
method described here has been used successfully on Windows 7, 8 and 10.  Vista 
should also work but has not been tested.


.. admonition:: technical note
   :class: note

   If you do not have Windows, yet still wish to produce an installer, 
   a virtual machine will suffice.  Virtual machine images are available  `here 
   from Microsoft 
   <https://developer.microsoft.com/en-us/microsoft-edge/tools/vms/>`_.

.. admonition:: already installed?
   :class: note

   There are many similarities to the usual installation process here.  if you 
   have already installed ghini.desktop you can skip the first two steps and 
   proceed to step 3 

#. Download and install the git, Python and PyGTK external dependencies as 
   outlined in the installation instructions.  You can use the direct links 
   provided here. (`git <Direct link to download git_>`_, `Python <Direct link 
   to download Python_>`_, `PyGTK <Direct link to download PyGTK_>`_) but 
   remember to select to put Python in the PATH and install **all** components 
   of PyGTK.

#. Download and install `Microsoft Visual C++ Compiler for Python 2.7 
   <http://aka.ms/vcpython27>`_.

#. Download and install `NSIS v3 <http://nsis.sourceforge.net/Download>`_.  
   (Unless you only wish to freeze the code - see below)

#. A **reboot** is recommended.

#. Clone ghini.desktop to wherever you want to keep it and checkout the branch 
   you wish to build.  To do this, open a command prompt and type these 
   commands::

      cd <path-to-wherever-you-want-to-keep-it>
      git clone https://github.com/Ghini/ghini.desktop.git
      cd ghini.desktop
      git checkout ghini-1.0

   .. admonition:: technical note
      :class: note

      If working in a Virtual machine this would be a good place to take 
      a snapshot. You will be able to immediately return to this point in the 
      process without waiting for the virtual machine to boot.

   .. admonition:: already installed?
      :class: note

      If you have already installed ghini.desktop following the installation 
      procedure you can just use that copy instead.  In this situation you would 
      only need to enter ``cd %HOMEPATH%\Local\github\Ghini\ghini.desktop`` for 
      this step.

#. Build the installer:  Assuming the command prompt from the last step is 
   still open (or just open a new one and ``cd <location-of-ghini.desktop>``) 
   run this command::

      scripts\build_win.bat

   This should leave a file named ``ghini.desktop-<version>-setup.exe`` in the 
   ``scripts`` folder of ghini.desktop.  This is your Windows installer.

   It is also worth noting that the ``dist`` folder will contain a full working 
   copy of the software in a frozen, self contained state, that can be 
   transferred however you like and will work in place.  (e.g.  placed on a USB 
   flash drive for demonstration purposes or copied manually to ``C:\Program 
   Files``).  If all you want is this frozen copy then you will not need to 
   install NSIS and can run the above command with the '/f' switch (i.e.  
   ``scripts\build_win.bat /f``).

In future if you wish to build further installers just open a command prompt 
and enter::

   cd <location-of-ghini.desktop>
   git pull
   scripts\build_win.bat

.. admonition:: technical note
   :class: note

   If you have been using a virtual machine as descibed here you would just 
   restore the snapshot and use ``git pull`` followed by 
   ``scripts\build_win.bat``


.. admonition:: about the installer
   :class: note

   -  The installer is capable of single user or global installs.

   -  At this point in time the ghini.desktop installed this way will not check
      or or notify you of any updated version.  You will need to check 
      yourself.

   -  The installer is capable of downloading extra components:

      -  Apache FOP - If you plan on using xslt templates to produce PDFs then 
         install FOP.  There is no uninstaller with this component.  FOP 
         requires the Java Runtime so if you do not currently have it installed 
         the ghini.desktop installer will let you know and can open the Oracle 
         web site for you to download and install it from.

      -  MS Visual C runtime - You most likely don't need this but if you have 
         any trouble getting ghini.desktop to run try installing the MS Visual 
         C runtime (rerun the installer and select this component only).

   -  Can be run silently using switches (e.g. for remote deployment) where:

      - ``/S`` for silent;

      - ``/AllUser`` or ``/CurrentUser``

      - ``/C=[gFC]`` to specify components where:

            g = Deselect the main ghini.desktop component (used for component 
            only installs)

            F = select Apache FOP

            C = select MS Visual C runtime


.. _Direct link to download git: https://github.com/git-for-windows/git/releases/download/v2.13.3.windows.1/Git-2.13.3-32-bit.exe
.. _Direct link to download Python: https://www.python.org/ftp/python/2.7.12/python-2.7.12.msi
.. _Direct link to download lxml: https://pypi.python.org/packages/2.7/l/lxml/lxml-3.6.0.win32-py2.7.exe
.. _Direct link to download PyGTK: http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/pygtk-all-in-one-2.24.2.win32-py2.7.msi
.. _Direct link to download psycopg2: http://www.stickpeople.com/projects/python/win-psycopg/2.6.1/psycopg2-2.6.1.win32-py2.7-pg9.4.4-release.exe

