from win32com.client import Dispatch
import os

base = os.path.expanduser("~\\Local\\github\\Ghini\\ghini.desktop")
path = os.path.join(base, 'scripts\\ghini.lnk')
target = os.path.join(base, "scripts\\bauble.vbs")
wDir = os.path.expanduser("~")
icon = os.path.join(base, "bauble\\images\\icon.ico")

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(path)
shortcut.Targetpath = target
shortcut.WorkingDirectory = wDir
shortcut.IconLocation = icon
shortcut.save()
