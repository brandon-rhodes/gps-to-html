#!/bin/bash

set -e
cd "$(dirname "${BASH_SOURCE[0]}")"
./generate.py test.template.html ~/Archive/garmin/*
