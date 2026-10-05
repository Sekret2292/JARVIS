' JARVIS - скрытый запуск UI без окна консоли
Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\JARVIS"
WshShell.Run """D:\JARVIS_DATA\Python313\python.exe"" ""D:\JARVIS\jarvis_ui_new.py""", 0, False
Set WshShell = Nothing