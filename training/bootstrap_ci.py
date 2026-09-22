import csv,json,numpy as np
csv.field_size_limit(10**9); rng=np.random.default_rng(2027)
ch=json.load(open('test_relabel_A.json'))['changes']
st={r['sent_id']:r['stratum'] for r in csv.DictReader(open('split2_test.csv'))}
rows=list(csv.DictReader(open('pred2_A_test.csv')))
def f1(g,p):
    tp=int(((g==1)&(p==1)).sum()); fp=int(((g==0)&(p==1)).sum()); fn=int(((g==1)&(p==0)).sum())
    P=tp/(tp+fp) if tp+fp else 0; R=tp/(tp+fn) if tp+fn else 0
    return P,R,(2*P*R/(P+R) if P+R else 0)
out={}
for lang in['en','ar']:
    R=[r for r in rows if r['lang']==lang]
    g=np.array([0 if (r['sent_id'] in ch and ch[r['sent_id']][0] in('none','artifact','Cloud')) else int(r['gold']) for r in R])
    # note: 'Cloud' entries in the container copy are the 7 rows relabelled none in v6
    pm=np.array([int(r['pred']) for r in R]); sp=np.array([st[r['sent_id']]=='screen_positive' for r in R]).astype(int)
    preds={'model':pm,'hybrid':pm*sp,'dictionary':sp}
    out[lang]={'n':len(R),'positives':int(g.sum())}
    for k,p in preds.items():
        P,Rc,F=f1(g,p); bs=[]
        for _ in range(2000):
            i=rng.integers(0,len(g),len(g)); bs.append(f1(g[i],p[i])[2])
        lo,hi=np.percentile(bs,[2.5,97.5])
        out[lang][k]={'P':round(P,3),'R':round(Rc,3),'F1':round(F,3),'F1_CI95':[round(lo,3),round(hi,3)]}
    # paired difference hybrid - dictionary
    d=[]
    for _ in range(2000):
        i=rng.integers(0,len(g),len(g)); d.append(f1(g[i],preds['hybrid'][i])[2]-f1(g[i],preds['dictionary'][i])[2])
    lo,hi=np.percentile(d,[2.5,97.5]); out[lang]['hybrid_minus_dictionary_F1']={'diff':round(float(np.mean(d)),3),'CI95':[round(lo,3),round(hi,3)]}
print(json.dumps(out,indent=1)); json.dump({'method':'nonparametric bootstrap, 2000 resamples of test sentences, seed 2027, percentile 95% CI; gold = master v6','runA':out},open('bootstrap_ci_A_v6.json','w'),indent=1)
