#!/bin/bash
for y in 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 2026; do
  f=data/raw/tle_bundles/$y/tle$y.txt
  if [ -f "$f" ]; then
    python3 src/00b_tle_parse.py "$f" 2>&1 | tee results/0b_tle_parse_$y.txt
  else
    echo "MISSING $f"
  fi
done
