"""Core functions shared by the app and the batch pipeline: text extraction, sentence split, dictionary screen, model, rule, measures."""
import re,json,os,unicodedata,html,collections
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
DICT_PATH=os.path.join(HERE,'dictionary.json')

# ---------- dictionary ----------
def load_dictionary(path=DICT_PATH):
    return json.load(open(path,encoding='utf-8'))
def save_dictionary(d,path=DICT_PATH):
    json.dump(d,open(path,'w',encoding='utf-8'),ensure_ascii=False,indent=1)

PROTECT={'الالي','الاليه','اليا','الى','الي','الآلي','الآلية'}
AR_IND=str.maketrans('٠١٢٣٤٥٦٧٨٩','0123456789')
def norm(s):
    s=unicodedata.normalize('NFKC',s).translate(AR_IND)
    s=re.sub(r'[ً-ْـ]','',s); s=re.sub('[أإآ]','ا',s).replace('ة','ه').replace('ى','ي').lower()
    s=re.sub(r'[-/]',' ',s); s=re.sub(r'[^\w؀-ۿ]+',' ',s)
    out=[w[2:] if (w.startswith('ال') and len(w)>=5 and w not in PROTECT) else w for w in s.split()]
    return ' '+' '.join(out)+' '

def compile_dictionary(d):
    """returns {lang: [(tech, norm_term, raw_term, rule)]}"""
    C={'en':[],'ar':[]}
    for tech,v in d.items():
        for lang in('en','ar'):
            for t in v['terms'][lang]:
                raw=t['term'].strip()
                if not raw: continue
                C[lang].append((tech,' '+norm(raw).strip()+' ',raw,t.get('rule','substring')))
    return C

def screen(text,lang,C):
    n=norm(text); techs=set()
    for tech,term,raw,rule in C[lang]:
        if rule=='substring':
            if term.strip() and term in n: techs.add(tech)
        else:
            if not re.search(r'\b'+re.escape(raw)+r'\b',text): continue
            if len(raw)<=2:   # AI, BI, ML need a co-term of the same technology
                other=any(tm in n for t2,tm,r2,ru in C[lang] if t2==tech and r2!=raw and tm.strip())
                if not other: continue
            techs.add(tech)
    return sorted(techs)

# ---------- text extraction ----------
def text_from_file(path):
    """returns list of (section, text). HTML/XBRL rendered pages, plain text, or PDF (English only, warned in UI)."""
    ext=os.path.splitext(path)[1].lower()
    if ext in('.html','.htm','.xhtml','.xml'):
        raw=open(path,encoding='utf-8',errors='ignore').read()
        facts=re.findall(r'<div class="fact"[^>]*data-concept="([^"]*)"[^>]*>(.*?)</div>',raw,re.S)
        if facts: return [(c,clean_html(t)) for c,t in facts]
        raw=re.sub(r'<(script|style)[^>]*>.*?</\1>',' ',raw,flags=re.S|re.I)
        return [('document',clean_html(raw))]
    if ext=='.pdf':
        import pdfplumber
        out=[]
        with pdfplumber.open(path) as pdf:
            for i,p in enumerate(pdf.pages):
                t=p.extract_text() or ''
                if t.strip(): out.append((f'page {i+1}',t))
        return out
    if ext=='.json':   # xbrljordan full-filing JSON: {'facts':[{elr, concept, lang, text(html)}]}
        j=json.load(open(path,encoding='utf-8')); facts=j.get('facts',j) if isinstance(j,dict) else j
        return [(f"{b.get('lang','')}|{b.get('elr','')}|{b.get('concept','')}",clean_html(b.get('text',''))) for b in facts if b.get('text')]
    return [('document',open(path,encoding='utf-8',errors='ignore').read())]

def clean_html(s):
    s=html.unescape(s); s=re.sub(r'<br\s*/?>|</p>|</li>|</tr>','\n',s,flags=re.I); s=re.sub(r'<[^>]+>',' ',s); s=html.unescape(s)
    s=unicodedata.normalize('NFKC',s); s=re.sub(r'[​-‏‪-‮⁦-⁩]','',s)
    return re.sub(r'[ \t]+',' ',s)

# ---------- sentences ----------
EN_ABBR={'mr','mrs','ms','dr','prof','inc','ltd','co','corp','plc','jsc','no','vs','etc','e.g','i.e','st','jr','sr','fig','vol','approx','dept','est'}
def split_sentences(text,lang):
    text=text.replace('\r','\n')
    if lang=='ar':
        parts=re.split(r'(?<=[.؟!])\s+|\n+',text)
    else:
        parts=[]; buf=''
        for tok in re.split(r'(\s+)',text):
            buf+=tok
            m=re.search(r'([A-Za-z0-9.]+)[.!?]$',tok.strip())
            if m or tok.endswith('\n'):
                w=tok.strip().rstrip('.!?').lower()
                if m and (w in EN_ABBR or re.fullmatch(r'[a-z]',w) or re.fullmatch(r'\d+',w)): continue
                parts.append(buf); buf=''
        parts.append(buf)
    out=[]
    for p in parts:
        p=re.sub(r'\s+',' ',p).strip()
        if len(p)<25: continue
        alpha=sum(ch.isalpha() for ch in p)/max(1,len(p.replace(' ','')))
        if alpha<0.6: continue
        out.append(p)
    return out

def detect_lang(text):
    ar=len(re.findall('[؀-ۿ]',text)); la=len(re.findall('[A-Za-z]',text))
    return 'ar' if ar>la else 'en'

def word_count(text): return len(re.findall(r'[\w؀-ۿ]+',text))

# ---------- model ----------
_model=None; _tok=None
def load_model(model_id=None):
    global _model,_tok
    if _model is not None: return _model,_tok
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    model_id=model_id or os.environ.get('DTI_MODEL','')
    if model_id and os.path.isdir(model_id) or (model_id and '/' in model_id and not model_id.endswith('.pt')):
        _tok=AutoTokenizer.from_pretrained(model_id); _model=AutoModelForSequenceClassification.from_pretrained(model_id)
    else:
        _tok=AutoTokenizer.from_pretrained('xlm-roberta-base'); _model=AutoModelForSequenceClassification.from_pretrained('xlm-roberta-base',num_labels=2)
        pt=model_id or os.path.join(HERE,'best_A.pt')
        _model.load_state_dict(torch.load(pt,map_location='cpu'))
    _model.eval(); return _model,_tok

def model_probs(texts):
    import torch
    m,t=load_model(); out=[]
    with torch.no_grad():
        for i in range(0,len(texts),32):
            e=t(texts[i:i+32],truncation=True,max_length=128,padding=True,return_tensors='pt')
            out+=torch.softmax(m(**e).logits,-1)[:,1].tolist()
    return out
THRESHOLD=float(os.environ.get('DTI_THRESHOLD','0.12'))

# ---------- full pipeline on one document ----------
def code_document(sections,lang,C,validated,threshold=THRESHOLD):
    from commitment_rule import commitment
    n_words=sum(word_count(t) for _,t in sections)
    rows=[]; seen=set()
    for sec,t in sections:
        for s in split_sentences(t,lang):
            key=s.lower()
            if key in seen: continue
            techs=screen(s,lang,C)
            if not techs: continue
            seen.add(key); rows.append({'section':sec,'text':s,'screen':techs})
    if rows:
        # model decides presence only for validated technologies; user-added technologies run in dictionary mode
        need=[i for i,r in enumerate(rows) if any(t in validated for t in r['screen'])]
        probs=model_probs([rows[i]['text'] for i in need]) if need else []
        pm={i:p for i,p in zip(need,probs)}
        for i,r in enumerate(rows):
            val=[t for t in r['screen'] if t in validated]; new=[t for t in r['screen'] if t not in validated]
            p=pm.get(i); present_val=(p is not None and p>=threshold)
            techs=(val if present_val else [])+new
            r['prob']=None if p is None else round(p,3)
            r['present']=1 if techs else 0
            r['technology']='none' if not techs else (techs[0] if len(techs)==1 else 'multiple')
            r['technologies']=';'.join(techs)
            r['mode']='model' if val and not new else ('dictionary' if new and not val else 'mixed')
            c=commitment(r['text'],lang) if techs else {'subject_ok':False,'verb_from_list':False,'verb':None,'tier':0}
            r.update({'subject_ok':c['subject_ok'],'verb_from_list':c['verb_from_list'],'verb':c['verb'] or '','tier':c['tier']})
    pos=[r for r in rows if r['present']]
    techset=set(t for r in pos for t in r['technologies'].split(';') if t)
    measures={'n_words':n_words,'n_screen':len(rows),'n_tech_sentences':len(pos),'density_per_10k_words':round(len(pos)/n_words*10000,3) if n_words else 0,
              'diversity':len(techset),'n_tier2':sum(r['tier']==2 for r in pos),'commitment_share':round(sum(r['tier']==2 for r in pos)/len(pos),3) if pos else 0,
              **{t:sum(t in r['technologies'].split(';') for r in pos) for t in C_techs(C)}}
    return rows,measures
def C_techs(C): return sorted(set(t for lang in C for t,_,_,_ in C[lang]))
