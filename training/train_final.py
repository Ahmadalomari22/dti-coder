"""Final model: run A settings (xlm-roberta-base, frozen embeddings, class-weighted CE, lr 3e-5, batch 16, max_len 128),
trained on train + val of split 2 (both languages) for the epoch count selected on val in run A (5). Threshold fixed at 0.12 (run A val).
Saved in Hugging Face format to model_final/. Evaluated once on the held-out firms for the record."""
import csv,json,time,random,os,numpy as np,torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix
csv.field_size_limit(10**9); SEED=42; EPOCHS=5; LR=3e-5; BS=16; MAXLEN=128; THR=0.12
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED); torch.set_num_threads(2)
def load(f): return list(csv.DictReader(open(f,encoding='utf-8')))
tr=load('split2_train.csv')+load('split2_val.csv'); te=load('split2_test_v6.csv')
tok=AutoTokenizer.from_pretrained('xlm-roberta-base'); model=AutoModelForSequenceClassification.from_pretrained('xlm-roberta-base',num_labels=2,id2label={0:'none',1:'technology'},label2id={'none':0,'technology':1})
for p in model.roberta.embeddings.parameters(): p.requires_grad=False
def enc(rows):
    e=tok([r['text'] for r in rows],truncation=True,max_length=MAXLEN,padding=True,return_tensors='pt'); return e,torch.tensor([int(r['label_binary']) for r in rows])
y=np.array([int(r['label_binary']) for r in tr]); cnt=np.bincount(y,minlength=2).astype(float); w=torch.tensor(len(tr)/(2*cnt),dtype=torch.float)
print('train n',len(tr),'pos',int(cnt[1]),flush=True)
opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=LR,weight_decay=0.01)
steps=EPOCHS*((len(tr)+BS-1)//BS); sch=get_linear_schedule_with_warmup(opt,int(0.1*steps),steps); lossf=torch.nn.CrossEntropyLoss(weight=w)
for ep in range(EPOCHS):
    model.train(); idx=list(range(len(tr))); random.shuffle(idx); t0=time.time(); tl=0
    for i in range(0,len(idx),BS):
        e,yb=enc([tr[j] for j in idx[i:i+BS]]); loss=lossf(model(**e).logits,yb); loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step(); sch.step(); opt.zero_grad(); tl+=loss.item()
    print(f'epoch {ep+1} loss {tl/((len(idx)+BS-1)//BS):.4f} {time.time()-t0:.0f}s',flush=True)
for p in model.parameters(): p.requires_grad=True
model.save_pretrained('model_final'); tok.save_pretrained('model_final')
model.eval(); res={'train_n':len(tr),'train_pos':int(cnt[1]),'epochs':EPOCHS,'threshold':THR}
with torch.no_grad():
    pt=[]
    for i in range(0,len(te),32):
        e,_=enc(te[i:i+32]); pt+=torch.softmax(model(**e).logits,-1)[:,1].tolist()
pt=np.array(pt)
for lang in('en','ar'):
    m=np.array([r['lang']==lang for r in te]); yy=np.array([int(r['label_binary']) for r in te])[m]; sp=np.array([r['stratum']=='screen_positive' for r in te])[m].astype(int)
    for name,pred in (('model',(pt[m]>=THR).astype(int)),('hybrid',(pt[m]>=THR).astype(int)*sp)):
        pr,rc,f,_=precision_recall_fscore_support(yy,pred,average='binary',pos_label=1,zero_division=0)
        res[f'test_{lang}_{name}']={'precision':round(pr,3),'recall':round(rc,3),'f1':round(f,3),'n':int(len(yy)),'positives':int(yy.sum())}
    print(lang,res[f'test_{lang}_model'],res[f'test_{lang}_hybrid'],flush=True)
json.dump(res,open('results_final.json','w'),indent=1)
with open('pred_final_test.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['sent_id','lang','gold','prob','pred','text'])
    for r,p in zip(te,pt): w.writerow([r['sent_id'],r['lang'],r['label_binary'],round(float(p),4),int(p>=THR),r['text']])
print('DONE',flush=True)
