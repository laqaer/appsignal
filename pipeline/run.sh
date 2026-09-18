#!/bin/sh
cd "$(dirname "$0")/.." && python3 pipeline/ingest.py && python3 pipeline/estimate.py
