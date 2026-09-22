# Model

`Ahmadalomari22/dti-coder-xlmr` on the Hugging Face Hub: xlm-roberta-base fine-tuned (embeddings frozen, class-weighted cross-entropy, lr 3e-5, batch 16, max length 128, 5 epochs) on 996 hand-coded sentences (192 positive) from Jordanian annual reports in Arabic and English. Binary output: technology mention present / absent. Decision threshold 0.12 (selected on validation). Technology label is assigned by the dictionary; commitment tier by `rule/commitment_rule.py`.
