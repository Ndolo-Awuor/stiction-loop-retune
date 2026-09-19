#!/bin/bash
# Always writes /logs/verifier/reward.txt (exactly 0 or 1), including on crashes.
mkdir -p /logs/verifier
echo -n 0 > /logs/verifier/reward.txt

pytest --ctrf /logs/verifier/ctrf.json /tests/test_retune.py -rA
if [ $? -eq 0 ]; then
    echo -n 1 > /logs/verifier/reward.txt
fi
exit 0
