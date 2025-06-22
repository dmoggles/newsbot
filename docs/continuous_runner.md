# Continuous News Aggregator Runner

This script runs the news aggregation pipeline continuously with configurable intervals and logging options.

## Usage

```bash
python continuous_runner.py [OPTIONS]
```

## Options

- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set the logging level (default: INFO)
- `--log-file LOG_FILE`: Path to the log file (default: newsbot.log)
- `--no-log-file`: Disable logging to file, log to console only
- `--interval INTERVAL`: Interval between runs (e.g., '30s', '5m', '2h', '1800'). Default: 30m
- `--max-iterations MAX_ITERATIONS`: Maximum number of iterations to run (default: unlimited)
- `--stop-on-error`: Stop the runner if an error occurs during pipeline execution

## Examples

Run with default settings (30-minute intervals, INFO logging to file):
```bash
python continuous_runner.py
```

Run every 5 minutes with DEBUG logging:
```bash
python continuous_runner.py --interval 5m --log-level DEBUG
```

Run every hour with console-only logging:
```bash
python continuous_runner.py --interval 1h --no-log-file --log-level INFO
```

Run with custom log file and stop after 10 iterations:
```bash
python continuous_runner.py --interval 30s --log-file custom.log --max-iterations 10
```

Run with error stopping enabled:
```bash
python continuous_runner.py --interval 15m --stop-on-error
```

## Interval Formats

The `--interval` parameter supports several formats:
- `30` or `30s`: 30 seconds
- `5m`: 5 minutes
- `2h`: 2 hours
- `300`: 300 seconds (5 minutes)

## Graceful Shutdown

The runner handles shutdown signals gracefully:
- Press `Ctrl+C` or send `SIGINT`/`SIGTERM` to stop
- The runner will complete the current iteration before stopping
- Final statistics will be logged on shutdown

## Features

- **Continuous Operation**: Runs the news aggregation pipeline in a loop
- **Configurable Intervals**: Set custom intervals between runs
- **Flexible Logging**: Choose log level and whether to log to file or console
- **Error Handling**: Option to continue or stop on errors
- **Graceful Shutdown**: Handles interruption signals properly
- **Statistics Tracking**: Logs iteration counts, errors, and runtime statistics
- **Signal Handling**: Responds to SIGINT and SIGTERM for clean shutdown
