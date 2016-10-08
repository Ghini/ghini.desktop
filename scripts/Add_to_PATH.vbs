' simple script used by the nsis installer to prepend to the PATH
' usage examples:
' >cscript.exe Add_to_PATH.vbs /path:"C:\TEST" /env:"USER" 
' >cscript.exe //E:vbscript Add_to_PATH.vbs /env:"SYSTEM" /path:"C:\TEST\"

Dim wshShell : Set wshShell = CreateObject("WScript.Shell")
Dim strPathToAdd : strPathToAdd = WScript.Arguments.Named("path")
Dim strEnv : strEnv = WScript.Arguments.Named("env")

Dim wshSysEnv : Set wshSysEnv = wshShell.Environment(strEnv)
Dim strCurrentPath : strCurrentPath = wshSysEnv("PATH")

Dim strNewPath : strNewPath = strPathToAdd & ";" & strCurrentPath
wshSysEnv("PATH") = strNewPath