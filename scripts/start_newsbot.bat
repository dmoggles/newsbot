@echo off
REM Startup batch file for the Continuous News Aggregator Runner
REM
REM This batch file starts the continuous runner with predefined settings:
REM - 1 minute intervals between runs
REM - No maximum iterations (runs indefinitely)
REM - INFO logging level
REM - Console-only logging (no log file)

echo ============================================================
echo Starting Continuous News Aggregator Runner
echo ============================================================
echo Settings:
echo   - Interval: 1 minute
echo   - Max iterations: Unlimited
echo   - Log level: INFO
echo   - Log output: Console only
echo ============================================================
echo.
echo Press Ctrl+C to stop the runner gracefully
echo.

REM Change to the parent directory (where continuous_runner.py is located)
cd /d "%~dp0\.."

REM Start the continuous runner
poetry run python continuous_runner.py --interval 1m --no-log-file --log-level INFO

echo.
echo Newsbot runner has stopped.
pause
