@echo off
rem Starts Symmetry on Windows by running start.sh with Git Bash, so it can be
rem used from Command Prompt, PowerShell or by double-clicking this file.
rem It takes the same commands as start.sh, for example:
rem     start-windows.cmd             (start backend and frontend)
rem     start-windows.cmd backend
rem     start-windows.cmd status
setlocal

rem Git for Windows puts git.exe in <Git>\cmd and bash.exe in <Git>\bin.
rem The plain "bash" command is avoided on purpose: on many machines it is the
rem WSL (Linux) bash, which can't use the Windows Python and Node installs.
set "BASH_EXE="
for /f "delims=" %%G in ('where git 2^>nul') do (
    if not defined BASH_EXE if exist "%%~dpG..\bin\bash.exe" set "BASH_EXE=%%~dpG..\bin\bash.exe"
)
if not defined BASH_EXE if exist "%ProgramFiles%\Git\bin\bash.exe" set "BASH_EXE=%ProgramFiles%\Git\bin\bash.exe"

if not defined BASH_EXE (
    echo Git Bash was not found. Install Git for Windows from https://git-scm.com/download/win
    exit /b 1
)

"%BASH_EXE%" "%~dp0start.sh" %*
