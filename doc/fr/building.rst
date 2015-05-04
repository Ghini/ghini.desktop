Building the source
========================

Building a python program is a bit of a contraddiction.  You don't normally
`build` nor `compile` a python program, you run it in its environment, and
python will process the modules loaded and produce faster-loading `compiled`
python files.  You can, however, produce a Windows executable from a python
script, executable containing the whole python environment and dependencies.

Building (on Windows)
---------------------

1. In order to build a Bauble executable you will first need to download the
   source code.  For more information about download the Bauble source go to
   :doc:`devdl`.

2. Follow all steps needed to set up a working Bauble environment from
   :doc:`installing`, but skip the final `install` step.

3. instead of `installing` Bauble, you produce a Windows executable.  This
   is achieved with the ``py2exe`` target, which is only available on
   Windows systems::

		 python setup.py py2exe

4. At this point you can run Bauble.  To run the compiled executable run::

		.\dist\bauble.exe

   or copy the executable to wherever you think appropriate.

6. To optionally build an NSIS installer package you must install NSIS
   from `nsis.sourceforge.net
   <http://nsis.sourceforge.net/Download>`_.  After installing NSIS
   right click on ``.\scripts\build.nsi`` in Explorer and select
   *Compile NSIS Script*.
