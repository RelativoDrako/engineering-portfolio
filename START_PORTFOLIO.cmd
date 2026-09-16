@echo off
setlocal
set "PORTFOLIO_ROOT=%~dp0"
cd /d "%PORTFOLIO_ROOT%"

if exist "%PORTFOLIO_ROOT%.venv\Scripts\python.exe" (
  "%PORTFOLIO_ROOT%.venv\Scripts\python.exe" -m portfolio_operator.bootstrap %*
) else (
  where py >nul 2>&1
  if errorlevel 1 (
    python -m portfolio_operator.bootstrap %*
  ) else (
    py -3 -m portfolio_operator.bootstrap %*
  )
)

set "PORTFOLIO_EXIT=%ERRORLEVEL%"
if not "%PORTFOLIO_EXIT%"=="0" (
  echo.
  echo Portfolio startup did not complete. Review the message above.
  pause
)
exit /b %PORTFOLIO_EXIT%
