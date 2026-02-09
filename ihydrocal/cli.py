"""Command-line interface for iHydroCal."""

import argparse
import sys
from . import __version__


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="iHydroCal - Integrated Hydrological Model Calibration"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"iHydroCal {__version__}",
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
