# CAN Log Workbench

A small offline analyzer for Classic CAN CSV logs, with JSON and HTML output.
**Status: runnable prototype.** Python standard library only; no dependency installation required.

## Quickstart on Windows

Requires Python 3.10 or later. From this folder in PowerShell:

```powershell
py analyze.py sample.csv --out out --data-kind synthetic
Start-Process .\out\report.html
py -m unittest discover -s tests -v
```

If the `py` launcher is unavailable, use `python` after checking `python --version`.
On Linux/macOS, use `python3` in place of `py` and open the HTML with your browser.
The tool refuses to overwrite an existing report; use another output directory for the next run.

`sample_output/report.html` is a generated example you can open immediately.

## CSV contract

```csv
timestamp_us,can_id,dlc,data
0,123,2,11 22
1000,123,2,11 23
```

- UTF-8 CSV; a UTF-8 BOM is accepted.
- Exactly four named columns; order may vary.
- `timestamp_us`: non-negative integer, non-decreasing across the file.
- `can_id`: hexadecimal 000–7FF, optionally prefixed with `0x`.
- `dlc`: integer 0–8; payload contains exactly that many space-separated hexadecimal bytes.
- Equal timestamps are preserved. Malformed rows reject the file with a line number.
- An empty log with a valid header produces an explicit empty report.

## Results in the sample

The sample is **synthetic**, created to demonstrate the parser. It is not data from the IMCOM experiment.

| ID | Frames | Payload bytes | Observed gaps (µs) |
|---|---:|---:|---|
| 000 | 1 | 0 | no interval |
| 123 | 4 | 8 | 1000, 1000, 2000 |
| 200 | 3 | 3 | 2000, 2000 |

The observation span is 4,500 µs. Gaps are computed **within each CAN ID**.

## Architecture

`CSV → strict parser → grouped summaries → JSON + HTML`

The HTML uses inline CSS and has no external scripts, fonts, or network requests.

## Limitations

- Only Classic CAN 11-bit data frames are supported; no CAN FD, extended IDs, or remote frames.
- The full log is held in memory; large-log streaming is a later milestone.
- Observed interarrival times are not MCU processing times.
- The report does not estimate bus utilization, frame loss, or realtime guarantees.
- `--data-kind` is a user-provided provenance label, not an automatic verification of the source.
- Tests were run in the preparation environment recorded in `VERIFICATION.md`; Windows execution still needs to be checked on the user's machine.

## Suggested next issues

1. Add an adapter for an actual log export from your CAN tool.
2. Add ID/time-range filtering with boundary tests.
3. Add a streaming aggregator for large logs and measure memory.
4. Add a timeline plot with source/configuration displayed.

This starter was generated with assistant help. Review, understand, and extend it;
describe your own additions and validation in your portfolio.
Choose a project license before public release. Python documentation: https://docs.python.org/3/library/csv.html.
