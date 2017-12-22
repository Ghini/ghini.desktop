' -Copyright (c) 2016,2017 Ross Demuth <rossdemuth123@gmail.com>
'
'  This file is part of ghini.desktop.
'
'  ghini.desktop is free software: you can redistribute it and/or modify
'  it under the terms of the GNU General Public License as published by
'  the Free Software Foundation, either version 3 of the License, or
'  (at your option) any later version.
'
'  ghini.desktop is distributed in the hope that it will be useful,
'  but WITHOUT ANY WARRANTY; without even the implied warranty of
'  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
'  GNU General Public License for more details.
'
'  You should have received a copy of the GNU General Public License
'  along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.

' a simple script used by the nsis installer to prepend to the PATH
'
' EXAMPLES:
' cscript.exe Add_to_PATH.vbs /path:"C:\TEST" /env:"USER"
' cscript.exe //E:vbscript Add_to_PATH.vbs /env:"SYSTEM" /path:"C:\TEST\"

Dim wshShell : Set wshShell = CreateObject("WScript.Shell")
Dim strPathToAdd : strPathToAdd = WScript.Arguments.Named("path")
Dim strEnv : strEnv = WScript.Arguments.Named("env")

Dim wshSysEnv : Set wshSysEnv = wshShell.Environment(strEnv)
Dim strCurrentPath : strCurrentPath = wshSysEnv("PATH")

Dim strNewPath : strNewPath = strPathToAdd & ";" & strCurrentPath
wshSysEnv("PATH") = strNewPath
