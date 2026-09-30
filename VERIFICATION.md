# Verification record

Prepared: 2026-09-30.

## Executed checks

- Environment: Linux, Python 3.12.14.
- Command: `python3 -m unittest discover -s tests -v`.
- Outcome: **9 test methods passed**; parameterized subcases include invalid IDs, payloads, timestamps and malformed headers.
- Command: `python3 analyze.py sample.csv --out sample_output --data-kind synthetic`.
- Outcome: 8 frames, 3 IDs, observation span 4,500 µs; HTML and JSON created.
- Output values were checked against the hand-calculated sample table in the README.
- Full test output is in `verification-output.txt`; error messages in negative tests are expected.

## Scope

The tests cover per-ID intervals, zero-length payloads, equal timestamps,
malformed inputs, empty logs, HTML escaping, report creation and preventing accidental report overwrite.

Windows commands are provided but have not been executed on a Windows host in this preparation.
The report's HTML was generated and its structure checked in tests; a browser visual review
could not be completed because the browser runtime was unavailable.

No MCU measurements, production CAN captures or large-log benchmarks were performed here.
The sample is synthetic and is not part of the IMCOM research data.
