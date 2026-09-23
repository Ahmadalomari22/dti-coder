"""Firm-grouped 5-fold cross-validation over all coded, non-artifact, non-duplicate sentences (split2 train+val+test = 1,648).
Same settings as run A: xlm-roberta-base, frozen embeddings, class-weighted CE, lr 3e-5, batch 16, max_len 128.
Per fold: 20% of the training firms form an inner validation set that selects the epoch (1..5) and the threshold; the
outer fold is scored once with those. Out-of-fold predictions are pooled and scored per language with a 2,000-resample bootstrap.
Dictionary baseline = stratum screen_positive. Hybrid = screen_positive AND model positive."""
import csv,json,time,random,os,sys
import numpy as np, torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from sklearn.metrics import precision_recall_fscore_support
csv.field_size_limit(10**9)
MODEL='xlm-roberta-base'; SEED=2027; EPOCHS=5; LR=3e-5; BS=16; MAXLEN=128; K=5
torch.set_num_threads(2)
def load(f): return list(csv.DictReader(open(f,encoding='utf-8')))
rows=load('split2_train.csv')+load('split2_val.csv')+load('split2_test_v6.csv')
for r in rows: r['y']=int(r['label_binary']); r['screen']=1 if r['stratum']=='screen_positive' else 0
firms=sorted(set(r['symbol'] for r in rows))
rng=random.Random(SEED)
# balance folds by positive count: sort firms by positives desc, deal round-robin after a seeded shuffle within ties
pos_by_firm={f:sum(r['y'] for r in rows if r['symbol']==f) for f in firms}
order=sorted(firms,key=lambda f:(-pos_by_firm[f],rng.random()))
fold_of={};
for i,f in enumerate(order): fold_of[f]=i%K
print('sentences',len(rows),'firms',len(firms),'positives',sum(r['y'] for r in rows),flush=True)
for k in range(K):
    te=[r for r in rows if fold_of[r['symbol']]==k]
    print('fold',k,'firms',len(set(r['symbol'] for r in te)),'n',len(te),'pos',sum(r['y'] for r in te),'en',sum(r['lang']=='en' for r in te),'ar',sum(r['lang']=='ar' for r in te),flush=True)
tok=AutoTokenizer.from_pretrained(MODEL)
def enc(rs):
    e=tok([r['text'] for r in rs],truncation=True,max_length=MAXLEN,padding=True,return_tensors='pt'); return e,torch.tensor([r['y'] for r in rs])
def probs(model,rs):
    model.eval(); out=[]
    with torch.no_grad():
        for i in range(0,len(rs),32):
            e,_=enc(rs[i:i+32]); out+=torch.softmax(model(**e).logits,-1)[:,1].tolist()
    return np.array(out)
def f1(y,pred):
    p,r,f,_=precision_recall_fscore_support(y,pred,average='binary',pos_label=1,zero_division=0); return p,r,f
def best_thr(y,p):
    best=(0,0.5)
    for t in np.arange(0.1,0.91,0.02):
        _,_,f=f1(y,(p>=t).astype(int))
        if f>best[0]: best=(f,t)
    return best
oof={}  # sent_id -> prob
fold_info=[]
for k in range(K):
    t0=time.time()
    tr_firms=[f for f in firms if fold_of[f]!=k]; rng2=random.Random(SEED+k); rng2.shuffle(tr_firms)
    n_in=max(1,int(round(0.2*len(tr_firms)))); inner=set(tr_firms[:n_in])
    tr=[r for r in rows if fold_of[r['symbol']]!=k and r['symbol'] not in inner]
    va=[r for r in rows if r['symbol'] in inner]
    te=[r for r in rows if fold_of[r['symbol']]==k]
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    model=AutoModelForSequenceClassification.from_pretrained(MODEL,num_labels=2)
    for p in model.roberta.embeddings.parameters(): p.requires_grad=False
    y=np.array([r['y'] for r in tr]); cnt=np.bincount(y,minlength=2).astype(float); w=torch.tensor(len(tr)/(2*cnt),dtype=torch.float)
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=LR,weight_decay=0.01)
    steps=EPOCHS*((len(tr)+BS-1)//BS); sch=get_linear_schedule_with_warmup(opt,int(0.1*steps),steps); lossf=torch.nn.CrossEntropyLoss(weight=w)
    yv=np.array([r['y'] for r in va]); best=None
    for ep in range(EPOCHS):
        model.train(); idx=list(range(len(tr))); random.shuffle(idx); tl=0
        for i in range(0,len(idx),BS):
            e,yb=enc([tr[j] for j in idx[i:i+BS]]); loss=lossf(model(**e).logits,yb); loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); sch.step(); opt.zero_grad(); tl+=loss.item()
        pv=probs(model,va); f,t=best_thr(yv,pv)
        print(f'fold {k} epoch {ep+1} loss {tl/((len(idx)+BS-1)//BS):.4f} inner-val f1 {f:.3f} thr {t:.2f} {time.time()-t0:.0f}s',flush=True)
        if best is None or f>best[0]: best=(f,ep+1,t); torch.save(model.state_dict(),f'cv_fold{k}.pt')
    model.load_state_dict(torch.load(f'cv_fold{k}.pt')); thr=float(best[2])
    pt=probs(model,te)
    for r,p in zip(te,pt): oof[r['sent_id']]=(float(p),thr)
    info={'fold':k,'train_n':len(tr),'train_pos':int(cnt[1]),'inner_val_n':len(va),'inner_val_pos':int(yv.sum()),'test_n':len(te),'test_pos':int(sum(r['y'] for r in te)),'best_epoch':best[1],'threshold':round(thr,2),'inner_val_f1':round(best[0],3)}
    for lang in ('en','ar'):
        rs=[r for r in te if r['lang']==lang]; yy=np.array([r['y'] for r in rs]); pp=np.array([oof[r['sent_id']][0] for r in rs])
        pm=(pp>=thr).astype(int); ph=pm*np.array([r['screen'] for r in rs]); pd_=np.array([r['screen'] for r in rs])
        info[lang]={'n':len(rs),'pos':int(yy.sum()),'model':[round(x,3) for x in f1(yy,pm)],'hybrid':[round(x,3) for x in f1(yy,ph)],'dictionary':[round(x,3) for x in f1(yy,pd_)]}
    fold_info.append(info); print('FOLD RESULT',json.dumps(info),flush=True)
    os.remove(f'cv_fold{k}.pt')
# pooled out-of-fold
res={'method':'firm-grouped 5-fold CV over 1,648 sentences (88 firms); inner 20% of training firms select epoch (1-5) and threshold per fold; pooled out-of-fold predictions; bootstrap 2,000 resamples seed 2027','folds':fold_info}
B=2000; rb=np.random.default_rng(SEED)
for lang in ('en','ar'):
    rs=[r for r in rows if r['lang']==lang]; yy=np.array([r['y'] for r in rs])
    pm=np.array([int(oof[r['sent_id']][0]>=oof[r['sent_id']][1]) for r in rs]); sc=np.array([r['screen'] for r in rs]); ph=pm*sc
    out={'n':len(rs),'positives':int(yy.sum())}
    for name,pred in (('model',pm),('hybrid',ph),('dictionary',sc)):
        p,r,f=f1(yy,pred); out[name]={'P':round(p,3),'R':round(r,3),'F1':round(f,3)}
    fs={'model':[],'hybrid':[],'dictionary':[]}; diffs=[]
    for b in range(B):
        ix=rb.integers(0,len(rs),len(rs)); yb=yy[ix]
        for name,pred in (('model',pm),('hybrid',ph),('dictionary',sc)): fs[name].append(f1(yb,pred[ix])[2])
        diffs.append(fs['hybrid'][-1]-fs['dictionary'][-1])
    for name in fs: out[name]['F1_CI95']=[round(float(np.percentile(fs[name],2.5)),3),round(float(np.percentile(fs[name],97.5)),3)]
    d=np.array(diffs); out['hybrid_minus_dictionary_F1']={'diff':round(out['hybrid']['F1']-out['dictionary']['F1'],3),'CI95':[round(float(np.percentile(d,2.5)),3),round(float(np.percentile(d,97.5)),3)],'P_diff_le_0':round(float((d<=0).mean()),3)}
    res[lang]=out; print('POOLED',lang,json.dumps(out),flush=True)
json.dump(res,open('results_cv_grouped.json','w'),indent=1)
with open('pred_cv_oof.csv','w',newline='',encoding='utf-8') as f:
    wr=csv.writer(f); wr.writerow(['sent_id','symbol','lang','fold','gold','screen','prob','threshold','pred_model','pred_hybrid'])
    for r in rows:
        p,t=oof[r['sent_id']]; wr.writerow([r['sent_id'],r['symbol'],r['lang'],fold_of[r['symbol']],r['y'],r['screen'],round(p,4),t,int(p>=t),int(p>=t)*r['screen']])
print('DONE',flush=True)
