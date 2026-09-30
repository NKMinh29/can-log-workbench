import io
from pathlib import Path
import tempfile
import unittest

from analyze import main, read_frames, summarize, render_html

HEADER = 'timestamp_us,can_id,dlc,data\n'


class CANLogTests(unittest.TestCase):
    def parse(self, body):
        return read_frames(io.StringIO(HEADER + body))

    def test_interarrival_is_per_id_and_uses_all_intervals(self):
        frames = self.parse('0,123,1,AA\n500,200,1,BB\n1000,123,1,CC\n4000,123,1,DD\n')
        report = summarize(frames, 'test', 'synthetic')
        self.assertEqual(report['frame_count'], 4)
        self.assertEqual(report['by_id'][0]['observed_interarrival_us'],
                         {'count': 2, 'min': 1000, 'median': 2000.0, 'mean': 2000, 'max': 3000})
        self.assertIsNone(report['by_id'][1]['observed_interarrival_us']['mean'])

    def test_zero_length_payload_and_equal_timestamp(self):
        report = summarize(self.parse('0,000,0,\n0,000,0,\n'), 'test', 'synthetic')
        self.assertEqual(report['by_id'][0]['observed_interarrival_us']['min'], 0)
        self.assertEqual(report['by_id'][0]['payload_bytes'], 0)

    def test_rejects_invalid_can_and_payload(self):
        for row in ['0,800,0,\n', '0,001,9,\n', '0,001,2,AA\n', '0,001,1,GG\n', '0,001,1,A\n']:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, 'Line 2'):
                self.parse(row)

    def test_rejects_decreasing_or_invalid_timestamp(self):
        for body in ['10,001,0,\n9,001,0,\n', '-1,001,0,\n', 'NaN,001,0,\n']:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.parse(body)

    def test_rejects_missing_extra_duplicate_columns(self):
        for data in ['"timestamp_us,can_id,dlc,data\n', 'timestamp_us,can_id,dlc,dlc\n', HEADER + '0,001,0\n', HEADER + '0,001,0,,extra\n']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                read_frames(io.StringIO(data))

    def test_empty_log_and_html_escaping(self):
        report = summarize(self.parse(''), '<script>alert(1)</script>', 'unspecified')
        self.assertIsNone(report['observation_span_us'])
        html = render_html(report)
        self.assertIn('No frames', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_cli_writes_reports_with_correct_sample(self):
        sample = Path(__file__).resolve().parents[1] / 'sample.csv'
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(main([str(sample), '--out', td, '--data-kind', 'synthetic']), 0)
            self.assertTrue((Path(td) / 'report.html').exists())
            self.assertIn('"frame_count": 8', (Path(td) / 'report.json').read_text())

    def test_cli_invalid_input_creates_no_report(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'bad.csv'
            p.write_text(HEADER + '0,001,8,AA\n')
            out = Path(td) / 'out'
            self.assertEqual(main([str(p), '--out', str(out)]), 2)
            self.assertFalse(out.exists())

    def test_cli_will_not_overwrite_existing_report(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'report.json'
            target.write_text('keep this')
            with self.assertRaises(SystemExit):
                main(['sample.csv', '--out', td])
            self.assertEqual(target.read_text(), 'keep this')


if __name__ == '__main__':
    unittest.main()
