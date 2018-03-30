@if (@X)==(@Y) @end /* Harmless hybrid line that begins a JScript comment

<<<<<<< HEAD
::--- http://stackoverflow.com/questions/10711839/
::--- http://stackoverflow.com/users/1012053/dbenham
::--- license CC:SA-BY
=======
::--- source: http://stackoverflow.com/questions/10711839/
::--- author: http://stackoverflow.com/users/1012053/dbenham
::--- license: CC:SA-BY
>>>>>>> ghini-1.0-dev

::--- Batch section within JScript comment that calls the internal JScript ----
@echo off
cscript //E:JScript //nologo "%~f0" %*
exit /b

----- End of JScript comment, beginning of normal JScript  ------------------*/
var fso = new ActiveXObject("Scripting.FileSystemObject");
var mode=2;
if (WScript.Arguments.Count()==2) {mode=8;}
var out = fso.OpenTextFile(WScript.Arguments(0),mode,true);
var chr;
while( !WScript.StdIn.AtEndOfStream ) {
  chr=WScript.StdIn.Read(1);
  WScript.StdOut.Write(chr);
  out.Write(chr);
}
