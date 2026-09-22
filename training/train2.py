import csv,json,sys,time,random,os
import numpy as np, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
csv.field_size_limit(10**9)
RUN=sys.argv[1]; TRAIN_LANGS=sys.argv[2].split(',')   # e.g. A en,ar  |  B en
MODEL='xlm-roberta-base'; SEED=42; EPOCHS=int(os.environ.get('EPOCHS','6')); LR=float(os.environ.get('LR','3e-5')); BS=16; MAXLEN=128
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.set_num_threads(2)
def load(f): return list(csv.DictReader(open(f,encoding='utf-8')))
tr=[r for r in load('split2_train.csv') if r['lang'] in TRAIN_LANGS]
va=load('split2_val.csv'); te=load('split2_test.csv')
tok=AutoTokenizer.from_pretrained(MODEL); model=AutoModelForSequenceClassification.from_pretrained(MODEL,num_labels=2)
for p in model.roberta.embeddings.parameters(): p.requires_grad=False
def enc(rows):
    e=tok([r['text'] for r in rows],truncation=True,max_length=MAXLEN,padding=True,return_tensors='pt')
    return e,torch.tensor([int(r['label_binary']) for r in rows])
y=np.array([int(r['label_binary']) for r in tr]); cnt=np.bincount(y,minlength=2).astype(float)
w=torch.tensor(len(tr)/(2*cnt),dtype=torch.float)
print('RUN',RUN,'train langs',TRAIN_LANGS,'n',len(tr),'pos',int(cnt[1]),'weights',[round(x,3) for x in w.tolist()],flush=True)
opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=LR,weight_decay=0.01)
steps=EPOCHS*((len(tr)+BS-1)//BS); sch=get_linear_schedule_with_warmup(opt,int(0.1*steps),steps)
lossf=torch.nn.CrossEntropyLoss(weight=w)
def probs(rows):
    model.eval(); out=[]
    with torch.no_grad():
        for i in range(0,len(rows),32):
            e,_=enc(rows[i:i+32]); out+=torch.softmax(model(**e).logits,-1)[:,1].tolist()
    return np.array(out)
def score(rows,p,thr):
    yy=np.array([int(r['label_binary']) for r in rows]); pred=(p>=thr).astype(int)
    pr,rc,f,_=precision_recall_fscore_support(yy,pred,average='binary',pos_label=1,zero_division=0)
    return {'precision':round(pr,4),'recall':round(rc,4),'f1':round(f,4),'confusion':confusion_matrix(yy,pred,labels=[0,1]).tolist(),'n':int(len(yy)),'positives':int(yy.sum()),'threshold':round(float(thr),3)}
def best_thr(rows,p):
    yy=np.array([int(r['label_binary']) for r in rows]); best=(0,0.5)
    for t in np.arange(0.1,0.91,0.02):
        _,_,f,_=precision_recall_fscore_support(yy,(p>=t).astype(int),average='binary',pos_label=1,zero_division=0)
        if f>best[0]: best=(f,t)
    return best
hist=[]; bestv=None
for ep in range(EPOCHS):
    model.train(); idx=list(range(len(tr))); random.shuffle(idx); t0=time.time(); tl=0
    for i in range(0,len(idx),BS):
        e,yb=enc([tr[j] for j in idx[i:i+BS]]); loss=lossf(model(**e).logits,yb); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); sch.step(); opt.zero_grad(); tl+=loss.item()
    pv=probs(va); f,t=best_thr(va,pv); s=score(va,pv,t)
    print(f'epoch {ep+1} loss {tl/((len(idx)+BS-1)//BS):.4f} {time.time()-t0:.0f}s | val f1@0.5 {score(va,pv,0.5)["f1"]} f1@best {s["f1"]} thr {t:.2f} P {s["precision"]} R {s["recall"]}',flush=True)
    hist.append({'epoch':ep+1,'val':s})
    if bestv is None or f>bestv[0]: bestv=(f,ep+1,t); torch.save(model.state_dict(),f'best_{RUN}.pt')
model.load_state_dict(torch.load(f'best_{RUN}.pt')); thr=bestv[2]
res={'run':RUN,'train_langs':TRAIN_LANGS,'train_n':len(tr),'train_pos':int(cnt[1]),'best_epoch':bestv[1],'threshold_from_val':round(float(thr),3),'history':hist}
pv=probs(va); res['val_all']=score(va,pv,thr)
pt=probs(te)
for lang in ('en','ar'):
    m=np.array([r['lang']==lang for r in te]); rows=[r for r in te if r['lang']==lang]
    res['test_'+lang]=score(rows,pt[m],thr)
    res['dict_precision_test_'+lang]=round(sum(1 for r in rows if r['stratum']=='screen_positive' and r['label_binary']=='1')/max(1,sum(1 for r in rows if r['stratum']=='screen_positive')),4)
    print('TEST',lang,json.dumps(res['test_'+lang]),'dict precision',res['dict_precision_test_'+lang],flush=True)
json.dump(res,open(f'results2_{RUN}.json','w'),indent=1)
with open(f'pred2_{RUN}_test.csv','w',newline='',encoding='utf-8') as f:
    wr=csv.writer(f); wr.writerow(['sent_id','lang','gold','prob','pred','text'])
    for r,p in zip(te,pt): wr.writerow([r['sent_id'],r['lang'],r['label_binary'],round(float(p),4),int(p>=thr),r['text']])
print('DONE',flush=True)
