# Malformed source-data fixtures

These fixtures intentionally mimic real-world TraceBack ingestion failures.
They are not validator evidence; they are defensive QA inputs for source-data integrity handling.

## Groups

- `invalid-json/`: bad JSON syntax, including interrupted or incomplete writes.
- `empty-or-placeholder/`: zero-byte and whitespace-only files from failed exports.
- `wrong-json-shape/`: valid JSON that is not TraceBack's expected array-of-records shape.
- `wrong-record-shape/`: arrays containing non-object rows/records from mixed pipeline output.
- `encoding-problems/`: Windows-adjacent encoding cases, including UTF-8 BOM files that should be accepted.
