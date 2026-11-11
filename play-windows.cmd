@echo off
setlocal
set "GAME=%~dp0dist\Saltline.html"
set "URL=file:///%GAME:\=/%"
set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME%" set "CHROME=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if exist "%CHROME%" (
  start "" "%CHROME%" --app="%URL%" --allow-file-access-from-files --autoplay-policy=no-user-gesture-required
) else (
  start "" "%GAME%"
)
endlocal
