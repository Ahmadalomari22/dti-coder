# DTI Coder

Bilingual (Arabic / English) measurement of Digital Technology Integration (DTI) in annual-report narrative. Built on 912 XBRL annual reports of Amman Stock Exchange firms (publication years 2021 to 2026); 326 paired filings read in full, both languages, all sections.

Ahmad Alomari and Anwar Allah Pitchay, School of Management, Universiti Sains Malaysia. Working paper in preparation.

## What it does

For every sentence: dictionary screen for six technologies (AI/ML, Big Data, Cloud, ERP, smart accounting and RPA, XBRL) → fine-tuned XLM-RoBERTa presence model → dictionary technology label → commitment rule (tier 2 = the reporting firm is the subject and a closed-list verb acts on a technology term; both conditions are output as columns so every code can be audited).

For every report: word count (full report), technology sentences, density per 10,000 words, diversity (technologies named), tier-2 count and share, counts per technology.

## Layout

| folder | content |
|---|---|
| `app/` | Gradio interface (code reports, edit or extend the dictionary, reliability and rules). Same files run locally or as a Hugging Face Space |
| `pipeline/` | batch pipeline: screened sentences → model → label → rule → report measures |
| `rule/` | `commitment_rule.py` (v3.1) and its evaluations against human coders, including the clean test |
| `training/` | training and evaluation scripts (binary run A/B, nine-class T9, final model, bootstrap CI) |
| `data/` | firm-grouped splits (no firm shared between partitions, either language), the 1,880 hand-coded sentences (master v6), dictionary v3 terms, exclusions |
| `results/` | held-out results, bootstrap CIs, LLM zero-shot robustness check, nine-class and hybrid label results, report-level measures for the 326 filings |
| `codebook/` | codebook: technology definitions, commitment rule with sub-rules f1 to f8, coding conventions |

Model weights: Hugging Face Hub (see `MODEL.md`). Set `DTI_MODEL=<hub id>` before running the app.

## Held-out performance (firms unseen in training, either language; 95% bootstrap CI)

| test set | n | positives | model F1 | hybrid F1 | dictionary F1 | LLM zero-shot F1 |
|---|---|---|---|---|---|---|
| English, 26 firms | 319 | 39 | 0.659 [0.53, 0.77] | 0.691 [0.56, 0.81] | 0.614 [0.50, 0.71] | 0.618 [0.47, 0.74] |
| Arabic, 27 firms | 333 | 28 | 0.787 [0.66, 0.89] | 0.814 [0.69, 0.91] | 0.533 [0.41, 0.65] | 0.647 [0.51, 0.77] |

Human reliability (round 3, 100 unseen sentences, two coders): binary kappa 0.851, technology 0.671, commitment 0.698. Commitment rule script vs human consensus on a fresh 100-sentence test: v3.0 (frozen before the test) 0.43 [0.19, 0.66]; v3.1 (adjusted after inspecting coder A) 0.71 [0.52, 0.88]. Details in `rule/`.

## Reproduce

```
pip install -r app/requirements.txt
python training/train_final.py        # needs data/split2_*.csv in the working directory
python pipeline/dti_pipeline.py       # needs the screened sentences and report totals
python app/app.py
```

## Licence

Code: MIT. Data, codebook and dictionary: CC BY 4.0. Source reports are public XBRL filings on xbrljordan.jo.

## Citation

Alomari, A. and Pitchay, A. A. (2026). DTI Coder: bilingual measurement of digital technology integration in annual-report narrative. Working paper, Universiti Sains Malaysia. https://github.com/Ahmadalomari22/dti-coder
