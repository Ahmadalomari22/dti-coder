import csv,json,numpy as np,torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import classification_report,f1_score
csv.field_size_limit(10**9); torch.set_num_threads(2)
LABELS=['none','AI/ML','Big Data','Cloud','ERP','SAR','XBRL','multiple']; L={l:i for i,l in enumerate(LABELS)}
def load(f): return list(csv.DictReader(open(f,encoding='utf-8')))
va=load('split2_val.csv'); te=load('split2_test_v6.csv')
tok=AutoTokenizer.from_pretrained('xlm-roberta-base'); model=AutoModelForSequenceClassification.from_pretrained('xlm-roberta-base',num_labels=8)
model.load_state_dict(torch.load('best_T9.pt')); model.eval()
def predict(rows):
    out=[]
    with torch.no_grad():
        for i in range(0,len(rows),32):
            e=tok([r['text'] for r in rows[i:i+32]],truncation=True,max_length=128,padding=True,return_tensors='pt'); out+=model(**e).logits.argmax(-1).tolist()
    return np.array(out)
def score(rows,p):
    yy=np.array([L[r['label_tech']] for r in rows])
    return {'macro_f1':round(f1_score(yy,p,average='macro',zero_division=0),4),'macro_f1_excl_none':round(f1_score(yy,p,labels=list(range(1,8)),average='macro',zero_division=0),4),'accuracy':round(float((yy==p).mean()),4),'n':len(yy),'report':classification_report(yy,p,labels=list(range(8)),target_names=LABELS,zero_division=0,output_dict=True)}
res={'run':'T9','note':'best checkpoint epoch 5 of 8 (run interrupted at epoch 7; val plateaued at epoch 5-6)','val':score(va,predict(va))}
pt=predict(te)
for lang in('en','ar'):
    m=np.array([r['lang']==lang for r in te]); res['test_'+lang]=score([r for r in te if r['lang']==lang],pt[m])
json.dump(res,open('results3_T9.json','w'),indent=1)
with open('pred3_T9_test.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['sent_id','lang','gold','pred','text'])
    for r,p in zip(te,pt): w.writerow([r['sent_id'],r['lang'],r['label_tech'],LABELS[p],r['text']])
for k in['val','test_en','test_ar']:
    print(k,{x:res[k][x] for x in['macro_f1','macro_f1_excl_none','accuracy']})
    for l,v in res[k]['report'].items():
        if l in LABELS: print('  ',l,'P',round(v['precision'],2),'R',round(v['recall'],2),'n',int(v['support']))
