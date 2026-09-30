"""Analyze a small Classic CAN CSV log using only the Python standard library."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from html import escape
import json
from pathlib import Path
import re
import statistics
import sys
from typing import TextIO


@dataclass(frozen=True)
class Frame:
    timestamp_us: int
    can_id: int
    payload: bytes


def read_frames(stream: TextIO) -> list[Frame]:
    reader = csv.DictReader(stream, strict=True)
    required = {"timestamp_us", "can_id", "dlc", "data"}
    try:
        headers = reader.fieldnames
    except csv.Error as error:
        raise ValueError(f"Invalid CSV header: {error}") from error
    if headers is None or set(headers) != required or len(headers) != 4:
        raise ValueError("Header must contain exactly: timestamp_us,can_id,dlc,data")
    frames: list[Frame] = []
    previous = -1
    try:
        for row in reader:
            line = reader.line_num
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Line {line}: expected four CSV columns")
            stamp_text, id_text = row["timestamp_us"].strip(), row["can_id"].strip()
            dlc_text, data_text = row["dlc"].strip(), row["data"].strip()
            if not re.fullmatch(r"[0-9]+", stamp_text):
                raise ValueError(f"Line {line}: timestamp_us must be a non-negative integer")
            stamp = int(stamp_text)
            if stamp < previous:
                raise ValueError(f"Line {line}: timestamps must not decrease")
            if not re.fullmatch(r"(?:0[xX])?[0-9a-fA-F]{1,3}", id_text):
                raise ValueError(f"Line {line}: can_id must be hexadecimal, 000 to 7FF")
            can_id = int(id_text, 16)
            if can_id > 0x7FF:
                raise ValueError(f"Line {line}: can_id exceeds 11-bit range")
            if not re.fullmatch(r"[0-8]", dlc_text):
                raise ValueError(f"Line {line}: dlc must be an integer from 0 to 8")
            tokens = data_text.split()
            if any(not re.fullmatch(r"[0-9a-fA-F]{2}", token) for token in tokens):
                raise ValueError(f"Line {line}: data must contain space-separated hex bytes")
            payload = bytes(int(token, 16) for token in tokens)
            if len(payload) != int(dlc_text):
                raise ValueError(f"Line {line}: payload length does not match DLC")
            frames.append(Frame(stamp, can_id, payload))
            previous = stamp
    except csv.Error as error:
        raise ValueError(f"Line {reader.line_num}: invalid CSV: {error}") from error
    return frames


def summarize(frames: list[Frame], source: str, data_kind: str) -> dict:
    grouped: dict[int, list[Frame]] = {}
    for frame in frames:
        grouped.setdefault(frame.can_id, []).append(frame)
    by_id = []
    for can_id, group in sorted(grouped.items()):
        gaps = [b.timestamp_us - a.timestamp_us for a, b in zip(group, group[1:])]
        by_id.append({
            "can_id": f"{can_id:03X}", "frames": len(group),
            "payload_bytes": sum(len(frame.payload) for frame in group),
            "observed_interarrival_us": {
                "count": len(gaps),
                "min": min(gaps) if gaps else None,
                "median": statistics.median(gaps) if gaps else None,
                "mean": statistics.mean(gaps) if gaps else None,
                "max": max(gaps) if gaps else None,
            },
        })
    return {
        "schema_version": 1, "source": source, "data_kind": data_kind,
        "frame_count": len(frames), "unique_ids": len(grouped),
        "first_timestamp_us": frames[0].timestamp_us if frames else None,
        "last_timestamp_us": frames[-1].timestamp_us if frames else None,
        "observation_span_us": frames[-1].timestamp_us - frames[0].timestamp_us if frames else None,
        "by_id": by_id,
        "limitations": [
            "Observed log interarrival times are not MCU processing times.",
            "Bus utilization and frame loss cannot be inferred from this report.",
            "Classic CAN 11-bit data frames only; the full file is held in memory.",
        ],
    }


def render_html(report: dict) -> str:
    def fmt(value):
        return "—" if value is None else f"{value:,.3f}".rstrip("0").rstrip(".")
    rows = []
    for item in report["by_id"]:
        gap = item["observed_interarrival_us"]
        cells = [item["can_id"], item["frames"], item["payload_bytes"],
                 fmt(gap["min"]), fmt(gap["median"]), fmt(gap["mean"]), fmt(gap["max"])]
        rows.append("<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in cells) + "</tr>")
    if not rows:
        rows.append('<tr><td colspan="7">No frames in this log.</td></tr>')
    notes = "".join(f"<li>{escape(x)}</li>" for x in report["limitations"])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CAN Log Workbench</title><style>
body{{margin:0;background:#f2f5f8;color:#182b3a;font:16px/1.6 system-ui,sans-serif}}
main{{max-width:1000px;margin:48px auto;padding:0 24px}}header p{{color:#486273}}
h1{{font-size:36px;margin:6px 0}}.tag{{font:700 12px/1.5 system-ui;letter-spacing:.12em;color:#126b61}}
.cards{{display:flex;flex-wrap:wrap;gap:16px;margin:28px 0}}.card{{background:white;padding:20px 28px;border-radius:12px;flex:1;min-width:140px}}
.card strong{{display:block;font-size:30px}}.table-wrap{{overflow:auto;background:white;border-radius:12px}}
table{{border-collapse:collapse;width:100%;white-space:nowrap}}th,td{{padding:14px 18px;text-align:right;border-bottom:1px solid #e7edf2}}
th:first-child,td:first-child{{text-align:left}}th{{font-size:13px;background:#e9f0f5}}.note{{margin-top:28px;color:#486273}}
</style></head><body><main><header><div class="tag">ENGINEERING TOOL / OFFLINE REPORT</div>
<h1>CAN Log Workbench</h1><p>Source: {escape(report['source'])} · Data: {escape(report['data_kind'])}</p></header>
<section class="cards" aria-label="Summary"><div class="card">Frames<strong>{report['frame_count']}</strong></div>
<div class="card">Unique IDs<strong>{report['unique_ids']}</strong></div>
<div class="card">Observation span (µs)<strong>{fmt(report['observation_span_us'])}</strong></div></section>
<h2>Observed interarrival times by ID</h2><div class="table-wrap"><table>
<thead><tr><th scope="col">CAN ID (hex)</th><th scope="col">Frames</th><th scope="col">Payload bytes</th>
<th scope="col">Min µs</th><th scope="col">Median µs</th><th scope="col">Mean µs</th><th scope="col">Max µs</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div><section class="note"><h2>Interpretation</h2><ul>{notes}</ul>
<p>Missing intervals are shown as — when an ID has fewer than two records.</p></section></main></body></html>'''


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, default=Path("out"))
    parser.add_argument("--data-kind", choices=["synthetic", "measured", "unspecified"], default="unspecified")
    args = parser.parse_args(argv)
    outputs = [args.out / "report.json", args.out / "report.html"]
    if args.input.resolve() in [p.resolve() for p in outputs]:
        parser.error("Output must not overwrite the input file")
    if any(path.exists() for path in outputs):
        parser.error("Output report already exists; choose a new --out directory")
    try:
        with args.input.open(encoding="utf-8-sig", newline="") as stream:
            frames = read_frames(stream)
        report = summarize(frames, args.input.name, args.data_kind)
        args.out.mkdir(parents=True, exist_ok=True)
        outputs[0].write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        outputs[1].write_text(render_html(report), encoding="utf-8")
    except (ValueError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    print(f"Analyzed {len(frames)} frames across {report['unique_ids']} IDs. Reports: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
