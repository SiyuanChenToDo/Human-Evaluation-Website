# Scientific Hypothesis Evaluation System

科学猜想报告人工评估网站 — Flask + SQLite

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initialize database (import reports, create reviewers, generate assignments)
python app.py --init

# 3. Start server
python app.py --port 5000

# 4. Open browser
# Reviewers: http://localhost:5000/login
# Admin:     http://localhost:5000/admin-login  (password: admin2025)
```

## Features

- 150 scientific hypothesis reports rendered with MathJax (LaTeX support)
- 5-dimension scoring: Novelty, Significance, Scientific Rigor, Clarity, Feasibility
- Overlapping assignment strategy (33% overlap, 50 reports double-reviewed)
- ICC and Krippendorff's Alpha reliability statistics
- Disagreement flagging (score diff > 3) for third-reviewer arbitration
- CSV data export

## Evaluation Dimensions

| Dimension | Key | Description |
|-----------|-----|-------------|
| Novelty | Nov | Originality and conceptual innovation |
| Significance | Sig | Academic/practical impact if confirmed |
| Scientific Rigor | Eff | Logical coherence, theoretical grounding, methodological soundness |
| Clarity | Cla | Writing quality, organization, presentation |
| Feasibility | Fea | Testability and practical feasibility of methods |

Each dimension scored 0-10 (integer).

## Database Schema

- `reports` — 150 cleaned reports (AI metadata removed)
- `reviewers` — evaluator identities
- `assignments` — report-reviewer mapping with overlap
- `scores` — submitted evaluations

## Public Access (ngrok)

```bash
ngrok http 5000
# Share the generated https://xxxx.ngrok-free.dev URL
```
