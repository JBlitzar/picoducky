#!/bin/bash
cd "$(dirname "$0")"

rm /Volumes/CIRCUITPY/*.py
cp empty/*.py /Volumes/CIRCUITPY/


echo "Done! Files copied to CIRCUITPY"