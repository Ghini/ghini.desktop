from win32com.client import Dispatch
import os

base = os.path.expanduser("~\\Local\\github\\Ghini\\ghini.desktop")
path = os.path.join(base, 'scripts\\ghini.lnk')
target = os.path.join(base, "scripts\\ghini.vbs")
wDir = os.path.join(base, 'scripts')
icon = os.path.join(base, "bauble\\images\\icon.ico")

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(path)
shortcut.Targetpath = target
shortcut.WorkingDirectory = wDir
shortcut.IconLocation = icon
shortcut.save()
