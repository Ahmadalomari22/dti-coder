"""DTI Coder, Streamlit version (Streamlit Community Cloud). Same core as the Gradio app."""
import os,io,json,random,tempfile
import streamlit as st, pandas as pd
from dti_core import *
from commitment_rule import commitment, EN_VERBS, AR_VERBS

st.set_page_config(page_title='DTI Coder',layout='wide')
if 'dict' not in st.session_state: st.session_state['dict']=load_dictionary()
DICT=st.session_state['dict']
def C_(): return compile_dictionary(DICT)
def validated(): return {k for k,v in DICT.items() if v.get('validated')}

@st.cache_resource(show_spinner='Loading the model from the Hugging Face Hub (first run only)...')
def _warm(): load_model(); return True

def code_sentence(text,lang=None):
    lang=lang or detect_lang(text); C=C_(); techs=screen(text,lang,C)
    if not techs: return {'language':lang,'screen':'no dictionary term','present':0,'technology':'none','tier':0}
    val=[t for t in techs if t in validated()]; new=[t for t in techs if t not in validated()]
    p=model_probs([text])[0] if val else None
    present=(p is not None and p>=THRESHOLD) or bool(new); tl=(val if (p is not None and p>=THRESHOLD) else [])+new
    c=commitment(text,lang) if present else None
    return {'language':lang,'screen':';'.join(techs),'model_prob':None if p is None else round(p,3),'present':int(present),
            'technology':('none' if not tl else (tl[0] if len(tl)==1 else 'multiple'))+(' (dictionary mode, unvalidated)' if new else ''),
            'subject_ok':c['subject_ok'] if c else '','verb_from_list':c['verb_from_list'] if c else '','verb':(c['verb'] or '') if c else '','tier':c['tier'] if c else 0}

def code_uploads(files,lang_choice):
    C=C_(); V=validated(); rows=[]; meas=[]; warn=[]
    for f in files:
        path=os.path.join(tempfile.mkdtemp(),f.name); open(path,'wb').write(f.getbuffer())
        try: sections=text_from_file(path)
        except Exception as e: warn.append(f'{f.name}: could not read ({e})'); continue
        groups={}
        if f.name.lower().endswith('.json') and any(sec.startswith(('en|','ar|')) for sec,_ in sections):
            for sec,t in sections: groups.setdefault(sec[:2],[]).append((sec[3:],t))
        else:
            full=' '.join(t for _,t in sections); groups[detect_lang(full) if lang_choice=='auto' else lang_choice]=sections
        for lang,secs in groups.items():
            if f.name.lower().endswith('.pdf') and lang=='ar': warn.append(f'{f.name}: Arabic PDF extraction is not validated; check the sentence table.')
            r,m=code_document(secs,lang,C,V)
            for x in r: rows.append({'file':f.name,'language':lang,**{k:x[k] for k in['section','text','technology','technologies','mode','prob','present','subject_ok','verb_from_list','verb','tier']}})
            meas.append({'file':f.name,'language':lang,**m})
    return pd.DataFrame(meas),pd.DataFrame(rows),warn

LIVE=[('The bank implemented an artificial intelligence credit-scoring system in 2024.','en'),('طبّق البنك أنظمة تعتمد الذكاء الاصطناعي في تقييم مخاطر الائتمان.','ar'),
      ('The company has access to cloud services through a third-party provider.','en'),('The company upgraded its ERP system and integrated it with a cloud platform.','en'),
      ('نولي أهمية كبيرة لتحليلات البيانات الضخمة في خدمة عملائنا.','ar'),('The company owns 100% of Lightning Gate for Cloud Services.','en')]
REL=pd.DataFrame([['Round 1 (development)','300 sentences','commitment 0.282','superseded: rule v3 written after this round'],
 ['Calibration session','30 sentences, two coders, discussed','commitment 0.777, agreement 86.7%','sub-rules f1 to f6 written here'],
 ['Round 2 (development)','300 sentences','commitment 0.444, technology 0.532','six technology definitions written after this round'],
 ['Round 3 (independent, unseen)','100 sentences, two coders','binary 0.851 [0.734, 0.952]; technology 0.671 [0.552, 0.778]; commitment 0.698 [0.575, 0.816]','the reliability figures reported for the codebook'],
 ['Arabic rule check','50 Arabic sentences, two coders','commitment 0.865; subject_ok 0.831; verb_from_list 0.839','sub-rules f7, f8'],
 ['Clean rule test','100 fresh sentences (50 EN, 50 AR), two coders','human commitment 0.57 (EN 0.63, AR 0.50); script v3.0 vs consensus 0.43 [0.19, 0.66]; v3.1 0.71 [0.52, 0.88]','v3.1 adjusted after inspecting coder A']],
 columns=['stage','sample','Cohen kappa (95% CI)','role'])
MODEL=pd.DataFrame([['English, 26 held-out firms',319,39,'0.659 [0.53, 0.77]','0.691 [0.56, 0.81]','0.614 [0.50, 0.71]','0.618 [0.47, 0.74]'],
 ['Arabic, 27 held-out firms',333,28,'0.787 [0.66, 0.89]','0.814 [0.69, 0.91]','0.533 [0.41, 0.65]','0.647 [0.51, 0.77]']],
 columns=['test set','n','positives','model F1','hybrid F1','dictionary F1','LLM zero-shot F1'])
RULES=[('Tier 2 needs both','the reporting firm or one of its units is the subject, and a verb from the closed list acts on a technology term; otherwise tier 1'),
 ('Closed verb list, English',', '.join(EN_VERBS.keys())),('Closed verb list, Arabic',', '.join(k for k in AR_VERBS.keys() if k!='ب+مصدر')+' (and the ب+masdar form)'),
 ('f1','a listed verb counts in participial or circumstantial form when it acts on the technology'),('f2','a nominalisation is not a verb'),
 ('f3','an implicit firm subject is accepted in a description of a service the firm provides'),('f4','a system, plan or tool as subject fails'),
 ('f5','passive voice without an agent fails'),('f6','a listed verb whose object is outside the six technologies does not count'),
 ('f7','"the company\'s plans / strategy / vision" as subject fails'),('f8','"made progress", "continued its journey" are not on the list'),
 ('Company names','a technology word inside a proper company name is not a mention'),('Commercial service','providing a technology as a service to customers is not adoption in the firm\'s own operations')]

st.title('DTI Coder')
st.caption('Bilingual (Arabic / English) measurement of Digital Technology Integration in annual-report narrative: dictionary screen, fine-tuned XLM-RoBERTa presence model, dictionary technology label, auditable commitment rule. Model: ahmadomari/dti-coder-xlmr. Code: github.com/Ahmadalomari22/dti-coder')
_warm()
t1,t2,t3=st.tabs(['1. Code reports','2. Technology dictionary','3. Reliability and rules'])

with t1:
    st.markdown('Upload rendered XBRL pages (.html), full-filing JSON from xbrljordan.jo, plain text, or PDF (English PDFs only are validated). Every screened sentence is shown with the model decision and the two rule columns.')
    files=st.file_uploader('Reports',accept_multiple_files=True,type=['html','htm','txt','pdf','json'])
    lang=st.radio('Language',['auto','en','ar'],horizontal=True)
    if st.button('Code',type='primary') and files:
        with st.spinner('Coding...'):
            mdf,sdf,warn=code_uploads(files,lang)
        for w in warn: st.warning(w)
        if len(mdf):
            st.subheader('Report measures'); st.dataframe(mdf,width='stretch')
            st.subheader('Sentences (audit table)'); st.dataframe(sdf.astype(str),width='stretch')
            buf=io.BytesIO()
            with pd.ExcelWriter(buf) as w: mdf.to_excel(w,sheet_name='report_measures',index=False); sdf.to_excel(w,sheet_name='sentences',index=False)
            st.download_button('Download Excel',buf.getvalue(),'dti_output.xlsx')
    st.subheader('Try one sentence')
    one=st.text_area('Sentence',height=80); onel=st.radio('Sentence language',['auto','en','ar'],horizontal=True,key='onel')
    if st.button('Code sentence') and one.strip(): st.json(code_sentence(one,None if onel=='auto' else onel))
    st.subheader('Live examples')
    st.dataframe(pd.DataFrame([[t]+[str(code_sentence(t,l).get(k,'')) for k in['technology','subject_ok','verb_from_list','verb','tier']] for t,l in LIVE],columns=['sentence','technology','subject_ok','verb_from_list','verb','tier']),width='stretch')

with t2:
    st.markdown('Each technology has an editable term list per language; edits take effect in screening immediately. A technology you add runs in **dictionary mode** (screen and rule only, model bypassed) and is flagged unvalidated until you check its precision on your own reports. A hosted app does not keep edits between sessions: download `dictionary.json` to keep them.')
    tech=st.selectbox('Technology',list(DICT.keys()))
    v=DICT[tech]; st.caption('validated' if v.get('validated') else 'unvalidated (dictionary mode)')
    desc=st.text_input('Description',v['description'])
    c1,c2=st.columns(2)
    en=c1.text_area('English terms, one per line','\n'.join(t['term'] for t in v['terms']['en']),height=250)
    ar=c2.text_area('Arabic terms, one per line','\n'.join(t['term'] for t in v['terms']['ar']),height=250)
    ex2=st.text_input('Example, tier 2',v['examples']['tier2']); ex1=st.text_input('Example, tier 1',v['examples']['tier1'])
    if st.button('Save changes',type='primary'):
        for lg,txt in(('en',en),('ar',ar)):
            old={t['term']:t for t in v['terms'][lg]}
            v['terms'][lg]=[old.get(x.strip(),{'term':x.strip(),'rule':'acronym' if (x.strip().isupper() and len(x.strip())<=5) else 'substring'}) for x in txt.split('\n') if x.strip()]
        v['description']=desc; v['examples']={'tier2':ex2,'tier1':ex1}; st.success(f'Saved {tech}. Active in screening now.')
    with st.expander('+ Add a new technology'):
        nn=st.text_input('Name (e.g. FinTech, Quantum)'); nd=st.text_input('Description ',key='nd')
        ne=st.text_area('English terms, comma-separated',key='ne'); na=st.text_area('Arabic terms, comma-separated',key='na')
        n2=st.text_input('Example, tier 2 ',key='n2'); n1=st.text_input('Example, tier 1 ',key='n1')
        if st.button('Add') and nn.strip() and nn.strip() not in DICT:
            DICT[nn.strip()]={'description':nd,'validated':False,'terms':{'en':[{'term':x.strip(),'rule':'substring'} for x in ne.split(',') if x.strip()],'ar':[{'term':x.strip(),'rule':'substring'} for x in na.split(',') if x.strip()]},'examples':{'tier2':n2,'tier1':n1}}
            st.success(f'Added {nn.strip()} in dictionary mode (unvalidated).'); st.rerun()
    with st.expander('Validate a technology on your reports'):
        st.markdown('Draws up to 50 sentences that hit this technology\'s terms in the reports you upload here; code each as 1 (true mention) or 0, then compute precision.')
        vf=st.file_uploader('Reports for validation',accept_multiple_files=True,key='vf')
        if st.button('Draw sample') and vf:
            C=C_(); hits=[]
            for f in vf:
                path=os.path.join(tempfile.mkdtemp(),f.name); open(path,'wb').write(f.getbuffer())
                try: secs=text_from_file(path)
                except Exception: continue
                lg=detect_lang(' '.join(t for _,t in secs))
                for sec,t in secs:
                    for s in split_sentences(t,lg):
                        if tech in screen(s,lg,C): hits.append({'file':f.name,'language':lg,'sentence':s,'correct (1/0)':''})
            random.seed(0); random.shuffle(hits); st.session_state['vdf']=pd.DataFrame(hits[:50])
        if 'vdf' in st.session_state and len(st.session_state['vdf']):
            ed=st.data_editor(st.session_state['vdf'],width='stretch',key='ved')
            if st.button('Compute precision'):
                col=ed['correct (1/0)'].astype(str).str.strip(); done=col.isin(['0','1'])
                if done.sum():
                    pr=(col[done]=='1').mean(); st.info(f'Dictionary precision for {tech} on your reports: {pr:.2f} ({int(done.sum())} coded). Below 0.60 means the term list needs tightening.')
                else: st.warning('Fill the last column with 1 or 0 first.')
    st.download_button('Download dictionary.json',json.dumps(DICT,ensure_ascii=False,indent=1),'dictionary.json')
    up=st.file_uploader('Load dictionary.json',type=['json'],key='dup')
    if up is not None:
        st.session_state['dict']=json.load(up); st.success('Dictionary loaded.'); st.rerun()

with t3:
    st.subheader('Human reliability, by stage'); st.dataframe(REL,width='stretch')
    st.subheader('Model performance on held-out firms (no firm shared with training, either language; 95% bootstrap CI)'); st.dataframe(MODEL,width='stretch')
    st.subheader('Commitment rule v3.1'); st.dataframe(pd.DataFrame(RULES,columns=['rule','statement']),width='stretch')
    st.caption('Corpus: 912 XBRL annual reports, Amman Stock Exchange, publication years 2021 to 2026, 182 firms; 326 paired filings read in full (all sections, both languages). XBRL filing has been mandatory since ASE Circular 129 (20 December 2020).')
