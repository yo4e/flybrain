#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== FlyBrain Codespaces first boot =="
echo "Repository: $ROOT"
echo "Python: $(python --version)"
echo
echo "1/3 Running offline tests before downloading real data..."
python -m pytest -q

echo
echo "2/3 Downloading/verifying MaleCNS and running the real-data integration check..."
echo "This downloads about 1.1 GB of public data and preprocessing can take several minutes."
python tools/real_check.py malecns

echo
echo "3/3 Showing cached dataset information..."
flybrain info malecns

echo
echo "FlyBrain is awake. 🪰"
echo "Reminder: connectivity is reconstructed source data; LIF dynamics and I/O mappings are modeled assumptions."
