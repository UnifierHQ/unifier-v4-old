#!/bin/bash

# Unifier run script for systems that use Bash (e.g. Linux/macOS)
# If you're using Docker, you don't need this.

FILEPATH="$(which python3)"

if [[ -z $FILEPATH ]]; then
  echo "Could not find a Python 3 installation."
  exit 1
fi

python3 ./boot/bootloader.py "$@"
