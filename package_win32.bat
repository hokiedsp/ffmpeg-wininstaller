@SET name=ffmpeg-winstaller

@REM if exist venv rmdir /s /q venv
if exist build rmdir /s /q build
REM if exist dist rmdir /s /q dist

@REM Python build - just includes .pyc not source code ok
pyinstaller -F -n %name% -c --add-data "src\setenv.bat;src" src\main.py 

@REM remove temporary build directory
if exist build rmdir /s /q build

