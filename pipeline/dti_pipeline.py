"""DTI pipeline: screen-positive sentences -> XLM-R presence model -> dictionary technology label -> commitment rule -> per-report DTI measures.
Inputs: pipeline_screen_positive.csv (screen output, deduped within filing), report_totals.csv (full-report word counts), best_A.pt (run A), threshold from results2_A.json.
Outputs: pipeline_sentences.csv (sentence level), dti_report_measures.csv (report level).
Measures per (symbol, pub_date, lang):
  n_words            full-report word count (denominator, all ELRs)
  n_tech_sentences   sentences the model accepts as technology mentions
  density            n_tech_sentences per 10,000 words
  diversity          number of distinct technologies among the six mentioned
  n_tier2            sentences meeting the commitment rule (firm subject + closed-list verb on a technology object)
  commitment_share   n_tier2 / n_tech_sentences (0 when no technology sentence)
  ai_ml, big_data, cloud, erp, sar, xbrl   sentence counts per technology (a 'multiple' sentence counts in each technology it names)
"""
import csv,json,sys,os,collections,numpy as np,torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from commitment_rule import commitment
csv.field_size_limit(10**9); torch.set_num_threads(2)
HERE=os.path.dirname(os.path.abspath(__file__))
THR=json.load(open(os.path.join(HERE,'..','results2_A.json')))['threshold_from_val']
rows=list(csv.DictReader(open('pipeline_screen_positive.csv',encoding='utf-8')))
tok=AutoTokenizer.from_pretrained('xlm-roberta-base'); model=AutoModelForSequenceClassification.from_pretrained('xlm-roberta-base',num_labels=2)
model.load_state_dict(torch.load(os.path.join(HERE,'..','best_A.pt'))); model.eval()
probs=[]
with torch.no_grad():
    for i in range(0,len(rows),32):
        e=tok([r['text'] for r in rows[i:i+32]],truncation=True,max_length=128,padding=True,return_tensors='pt')
        probs+=torch.softmax(model(**e).logits,-1)[:,1].tolist()
TECHS=['AI/ML','Big Data','Cloud','ERP','SAR','XBRL']
out=[]
for r,p in zip(rows,probs):
    present=int(p>=THR)
    hits=sorted(set(x.strip() for x in r['tech_hits'].split(';') if x.strip()))
    tech='none' if not present else (hits[0] if len(hits)==1 else 'multiple')
    c=commitment(r['text'],r['lang']) if present else {'subject_ok':False,'verb_from_list':False,'verb':None,'tier':0}
    out.append({'sent_id':r['sent_id'],'symbol':r['symbol'],'pub_date':r['pub_date'],'lang':r['lang'],'elr':r['elr'],'prob':round(p,4),'present':present,
                'technology':tech,'technologies':';'.join(hits) if present else '','subject_ok':c['subject_ok'],'verb_from_list':c['verb_from_list'],'verb':c['verb'] or '','tier':c['tier'],'text':r['text']})
with open('pipeline_sentences.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
# report level
tot={(r['symbol'],r['pub_date'],r['lang']):int(r['n_words']) for r in csv.DictReader(open('report_totals.csv'))}
agg=collections.defaultdict(lambda:{'n':0,'t2':0,'techs':set(),**{t:0 for t in TECHS}})
for o in out:
    if not o['present']: continue
    a=agg[(o['symbol'],o['pub_date'],o['lang'])]; a['n']+=1; a['t2']+=o['tier']==2
    for t in o['technologies'].split(';'):
        if t in TECHS: a['techs'].add(t); a[t]+=1
rep=[]
for k,nw in sorted(tot.items()):
    a=agg.get(k); n=a['n'] if a else 0; t2=a['t2'] if a else 0
    rep.append({'symbol':k[0],'pub_date':k[1],'lang':k[2],'n_words':nw,'n_tech_sentences':n,'density_per_10k_words':round(n/nw*10000,3) if nw else 0,
                'diversity':len(a['techs']) if a else 0,'n_tier2':t2,'commitment_share':round(t2/n,3) if n else 0,
                **{t.lower().replace('/','_').replace(' ','_'):(a[t] if a else 0) for t in TECHS}})
with open('dti_report_measures.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rep[0].keys())); w.writeheader(); w.writerows(rep)
print('sentences',len(out),'present',sum(o['present'] for o in out),'tier2',sum(o['tier']==2 for o in out),'reports',len(rep),'reports with >=1',sum(r['n_tech_sentences']>0 for r in rep))
