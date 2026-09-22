import csv,json,sys,time,random,os
import numpy as np, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from sklearn.metrics import precision_recall_fscore_support, classification_report, f1_score
csv.field_size_limit(10**9)
RUN='T9'; MODEL='xlm-roberta-base'; SEED=42; EPOCHS=8; LR=3e-5; BS=16; MAXLEN=128
LABELS=['none','AI/ML','Big Data','Cloud','ERP','SAR','XBRL','multiple']; L={l:i for i,l in enumerate(LABELS)}
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.set_num_threads(2)
def load(f): return list(csv.DictReader(open(f,encoding='utf-8')))
tr=load('split2_train.csv'); va=load('split2_val.csv'); te=load('split2_test_v6.csv')
tok=AutoTokenizer.from_pretrained(MODEL); model=AutoModelForSequenceClassification.from_pretrained(MODEL,num_labels=len(LABELS))
for p in model.roberta.embeddings.parameters(): p.requires_grad=False
def enc(rows):
    e=tok([r['text'] for r in rows],truncation=True,max_length=MAXLEN,padding=True,return_tensors='pt')
    return e,torch.tensor([L[r['label_tech']] for r in rows])
y=np.array([L[r['label_tech']] for r in tr]); cnt=np.bincount(y,minlength=len(LABELS)).astype(float)
w=torch.tensor(np.sqrt(len(tr)/(len(LABELS)*np.maximum(cnt,1))),dtype=torch.float)
print('counts',dict(zip(LABELS,cnt.astype(int).tolist())),'weights',[round(x,2) for x in w.tolist()],flush=True)
opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=LR,weight_decay=0.01)
steps=EPOCHS*((len(tr)+BS-1)//BS); sch=get_linear_schedule_with_warmup(opt,int(0.1*steps),steps)
lossf=torch.nn.CrossEntropyLoss(weight=w)
def predict(rows):
    model.eval(); out=[]
    with torch.no_grad():
        for i in range(0,len(rows),32):
            e,_=enc(rows[i:i+32]); out+=model(**e).logits.argmax(-1).tolist()
    return np.array(out)
def score(rows,p):
    yy=np.array([L[r['label_tech']] for r in rows])
    return {'macro_f1':round(f1_score(yy,p,average='macro',zero_division=0),4),'weighted_f1':round(f1_score(yy,p,average='weighted',zero_division=0),4),
            'macro_f1_excl_none':round(f1_score(yy,p,labels=list(range(1,len(LABELS))),average='macro',zero_division=0),4),
            'accuracy':round(float((yy==p).mean()),4),'n':int(len(yy)),
            'report':classification_report(yy,p,labels=list(range(len(LABELS))),target_names=LABELS,zero_division=0,output_dict=True)}
hist=[]; best=None
for ep in range(EPOCHS):
    model.train(); idx=list(range(len(tr))); random.shuffle(idx); t0=time.time(); tl=0
    for i in range(0,len(idx),BS):
        e,yb=enc([tr[j] for j in idx[i:i+BS]]); loss=lossf(model(**e).logits,yb); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); sch.step(); opt.zero_grad(); tl+=loss.item()
    s=score(va,predict(va)); print(f'epoch {ep+1} loss {tl/((len(idx)+BS-1)//BS):.4f} {time.time()-t0:.0f}s | val macroF1 {s["macro_f1"]} excl-none {s["macro_f1_excl_none"]} acc {s["accuracy"]}',flush=True)
    hist.append({'epoch':ep+1,'val_macro_f1':s['macro_f1'],'val_macro_f1_excl_none':s['macro_f1_excl_none']})
    if best is None or s['macro_f1']>best[0]: best=(s['macro_f1'],ep+1); torch.save(model.state_dict(),f'best_{RUN}.pt')
model.load_state_dict(torch.load(f'best_{RUN}.pt'))
res={'run':RUN,'labels':LABELS,'train_counts':dict(zip(LABELS,cnt.astype(int).tolist())),'best_epoch':best[1],'history':hist,'val':score(va,predict(va))}
pt=predict(te)
for lang in ('en','ar'):
    m=np.array([r['lang']==lang for r in te]); res['test_'+lang]=score([r for r in te if r['lang']==lang],pt[m])
    print('TEST',lang,{k:v for k,v in res['test_'+lang].items() if k!='report'},flush=True)
json.dump(res,open(f'results3_{RUN}.json','w'),indent=1)
with open(f'pred3_{RUN}_test.csv','w',newline='',encoding='utf-8') as f:
    wr=csv.writer(f); wr.writerow(['sent_id','lang','gold','pred','text'])
    for r,p in zip(te,pt): wr.writerow([r['sent_id'],r['lang'],r['label_tech'],LABELS[p],r['text']])
print('DONE',flush=True)
