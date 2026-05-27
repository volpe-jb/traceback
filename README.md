# TraceBack: Self-Correcting Evidence Validation for AI-Assisted DFIR

## What TraceBack Is

TraceBack is an evidence-validation application for AI-assisted digital forensics and incident response. It checks whether AI-generated claims about user activity are actually supported by forensic evidence, then corrects, contradicts, downgrades, or retracts unsupported findings.

The project uses Hermes Agent with ChatGPT as an alternative agentic harness, with local validation logic and normalized forensic evidence as the grounding layer.

In plain terms: TraceBack is designed to make an AI forensic assistant show its work, admit when it is wrong, and point back to the evidence that justified the correction.

## Starter Validation Goal

Validate whether AI-generated claims about user activity are accurate across three forensic evidence types: logon events, process execution, and browser activity.

## Current MVP Evidence Types

1. Windows Security Event Logs
2. Process execution artifacts
3. Browser activity and download evidence

## Starter Claim Set

- Logon claim: Allie successfully logged in at 10:15. Expected result: corrected.
- Process claim: Allie successfully opened Disk Management. Expected result: contradicted.
- Browser claim: Allie did not download the NIST PDF. Expected result: contradicted.

## How the MVP Works

TraceBack reviews AI-generated claims about user activity, checks each claim against normalized forensic evidence, and outputs:

- a structured investigative narrative
- an accuracy report
- execution logs
- evidence references for each finding

## Evidence Pipeline

```text
raw Windows artifacts
        -> extraction tool / parser
        -> normalized JSON evidence
        -> TraceBack validation engine
        -> corrected or contradicted findings
```

Current extraction tools shown in planning/demo materials:

- `python-evtx` for Windows Security event data
- `PECmd` for process execution evidence
- `sqlite3` for browser history and downloads

## Planned Next Evidence Type

The next evidence type being added after the MVP is registry / removable-device evidence using RegRipper. That future admin/removable-device extension is tracked in `Planning/MVP v. 0.2.md`.

## Why This Scope

The current scope is intentionally narrow enough to be explainable and testable, but broad enough to demonstrate meaningful validation across multiple evidence types. The goal is not to replace SIFT or every forensic parser. The goal is to prove a credible self-correcting validation loop with traceable evidence.

## Why This Matters

Many AI-assisted forensic workflows can produce confident but unsupported claims. TraceBack focuses on the correction step: checking those claims against evidence and producing an audit-friendly result instead of asking the user to trust a black box.

## Repository Status

This repository currently contains the planning, architecture, evidence, and demo-preparation materials for the TraceBack MVP.

## Related Notes

- `00 - Project Overview.md`
- `Planning/TraceBack MVP.md`
- `Planning/Why TraceBack Uses Normalized Evidence.md`
- `Evidence and Datasets/Evidence Plan.md`
- `Demo and Submission/Video Script.md`
