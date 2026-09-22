---
title: DTI Coder
emoji: 📊
sdk: gradio
app_file: app.py
pinned: false
---

# DTI Coder

Bilingual (Arabic / English) measurement of Digital Technology Integration (DTI) in annual-report narrative.

Pipeline per sentence: dictionary screen (six technologies: AI/ML, Big Data, Cloud, ERP, smart accounting and RPA, XBRL) → fine-tuned XLM-RoBERTa presence model → dictionary technology label → commitment rule (tier 2 = firm subject + closed-list verb acting on a technology term; the two conditions are shown as columns so every code can be audited).

Per report: word count (full report, all sections), technology sentences, density per 10,000 words, diversity, tier-2 count and share, counts per technology.

## Run locally
```
pip install -r requirements.txt
export DTI_MODEL=<huggingface model id or path to best_A.pt>
python app.py
```
Inputs: rendered XBRL pages (.html), full-filing JSON from xbrljordan.jo, plain text, or PDF (English PDFs only are validated).

## Tabs
1. Code reports: upload, code, audit table, Excel download, single-sentence tester, six live examples.
2. Technology dictionary: edit term lists per technology (effective immediately), add a technology (runs in dictionary mode, flagged unvalidated), validate it on your own reports (draw 50 hits, hand-code, precision). Dictionary is saved as `dictionary.json`; download it to keep your edits (a hosted Space does not persist them).
3. Reliability and rules: human reliability by stage, held-out model performance, the commitment rule with sub-rules f1 to f8.

## Files
`app.py` interface; `dti_core.py` extraction, sentence split, screen, model, measures; `commitment_rule.py` the rule; `dictionary.json` terms; `best_A.pt` model weights (or set `DTI_MODEL`).
