#!/usr/bin/env python3
"""
Continuous News Aggregator Runner for BlueSky

This script runs the news aggregation pipeline continuously in a loop with configurable intervals.
It provides command-line options to control logging behavior and execution parameters.
"""

import logging
import argparse
import sys
import time
import signal
from datetime import datetime
from typing import Any, List
import os

# Add src directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from main import run_once

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, _: Any) -> None:
    """Handle shutdown signals gracefully."""
    global shutdown_requested  # pylint: disable=global-statement
    logger.info("Shutdown signal received (signal %d). Will stop after current iteration...", signum)
    shutdown_requested = True


def setup_logging(level: str, log_to_file: bool = True, log_file: str = "newsbot.log") -> None:
    """
    Configure logging with the specified level and optional file output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to write logs to a file
        log_file: Path to the log file (used only if log_to_file is True)
    """  # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Create handlers list
    handlers: List[logging.Handler] = []
    handlers.append(logging.StreamHandler())

    if log_to_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    if log_to_file:
        logger.info("Logging configured at %s level with file output to %s", level.upper(), log_file)
    else:
        logger.info("Logging configured at %s level with console output only", level.upper())


def parse_time_interval(interval_str: str) -> int:
    """
    Parse time interval string into seconds.

    Supports formats like:
    - '30' or '30s' for 30 seconds
    - '5m' for 5 minutes
    - '2h' for 2 hours

    Returns:
        Number of seconds
    """
    interval_str = interval_str.strip().lower()

    if interval_str.endswith("s"):
        return int(interval_str[:-1])
    elif interval_str.endswith("m"):
        return int(interval_str[:-1]) * 60
    elif interval_str.endswith("h"):
        return int(interval_str[:-1]) * 3600
    elif interval_str.isdigit():
        return int(interval_str)
    else:
        raise ValueError(f"Invalid interval format: {interval_str}. Use formats like '30s', '5m', '2h', or just '30'")


def main() -> int:
    """
    Main entry point for the continuous news aggregator runner.

    Handles command-line arguments, sets up logging, and runs the news aggregation
    pipeline in a continuous loop with configurable intervals.
    """
    parser = argparse.ArgumentParser(
        description="Continuous News Aggregator Runner for BlueSky",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python continuous_runner.py --interval 30m --log-level INFO
  python continuous_runner.py --interval 1h --no-log-file --log-level DEBUG
  python continuous_runner.py --interval 300 --log-file custom.log
        """,
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default="newsbot.log",
        help="Path to the log file (default: newsbot.log)",
    )

    parser.add_argument(
        "--no-log-file",
        action="store_true",
        help="Disable logging to file, log to console only",
    )

    parser.add_argument(
        "--interval",
        type=str,
        default="30m",
        help="Interval between runs (e.g., '30s', '5m', '2h', '1800'). Default: 30m",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        help="Maximum number of iterations to run (default: unlimited)",
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the runner if an error occurs during pipeline execution",
    )

    args = parser.parse_args()

    # Parse interval
    try:
        interval_seconds = parse_time_interval(args.interval)
    except ValueError as e:
        print("Error parsing interval: %s" % e, file=sys.stderr)
        return 1

    # Setup logging
    try:
        log_to_file = not args.no_log_file
        setup_logging(args.log_level, log_to_file, args.log_file)
    except ValueError as e:
        print("Error setting up logging: %s" % e, file=sys.stderr)
        return 1

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 60)
    logger.info("Continuous News Aggregator Runner starting up...")
    logger.info("Interval: %d seconds (%s)", interval_seconds, args.interval)
    logger.info("Max iterations: %s", args.max_iterations or "unlimited")
    logger.info("Stop on error: %s", args.stop_on_error)
    logger.info("Log to file: %s", not args.no_log_file)
    if not args.no_log_file:
        logger.info("Log file: %s", args.log_file)
    logger.info("=" * 60)

    iteration = 0
    total_errors = 0
    start_time = datetime.now()

    try:
        while not shutdown_requested:
            iteration += 1
            iteration_start_time = datetime.now()

            logger.info("-" * 40)
            logger.info("Starting iteration %d at %s", iteration, iteration_start_time.strftime("%Y-%m-%d %H:%M:%S"))

            try:
                # Run the news aggregation pipeline
                run_once()
                logger.info("Iteration %d completed successfully", iteration)

            except Exception as e:
                total_errors += 1
                logger.error("Error in iteration %d: %s", iteration, e)
                logger.exception("Full traceback:")

                if args.stop_on_error:
                    logger.error("Stopping runner due to error (--stop-on-error flag is set)")
                    break
                else:
                    logger.info("Continuing despite error...")

            # Check if we've reached max iterations
            if args.max_iterations and iteration >= args.max_iterations:
                logger.info("Reached maximum iterations (%d), stopping runner", args.max_iterations)
                break

            if not shutdown_requested:
                iteration_end_time = datetime.now()
                iteration_duration = iteration_end_time - iteration_start_time

                logger.info("Iteration %d took %s", iteration, iteration_duration)
                logger.info("Waiting %d seconds until next iteration...", interval_seconds)

                # Sleep in small chunks to allow for responsive shutdown
                sleep_start = time.time()
                while time.time() - sleep_start < interval_seconds and not shutdown_requested:
                    time.sleep(min(1, interval_seconds - (time.time() - sleep_start)))

    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")

    except Exception as e:
        logger.error("Unexpected error in main loop: %s", e)
        logger.exception("Full traceback:")
        return 1

    finally:
        end_time = datetime.now()
        total_duration = end_time - start_time

        logger.info("=" * 60)
        logger.info("Continuous News Aggregator Runner shutting down...")
        logger.info("Total iterations completed: %d", iteration)
        logger.info("Total errors encountered: %d", total_errors)
        logger.info("Total runtime: %s", total_duration)
        logger.info("Average time per iteration: %s", total_duration / iteration if iteration > 0 else "N/A")
        logger.info("Shutdown completed at %s", end_time.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
