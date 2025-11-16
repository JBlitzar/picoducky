#!/bin/bash
cd "$(dirname "$0")"

rm /Volumes/CIRCUITPY/*.bin  # clear up space before copying over
cp pd-src/*.py /Volumes/CIRCUITPY/

# lib files
cp -R pd-src/lib/* /Volumes/CIRCUITPY/lib/

echo "Done! Files copied to CIRCUITPY"