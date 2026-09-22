"""DTI Coder: bilingual (Arabic / English) measurement of Digital Technology Integration in annual-report narrative.
Three tabs: 1) code reports, 2) technology dictionary (editable, extensible), 3) reliability and rules.
Run locally:  pip install -r requirements.txt && python app.py
"""
import os,io,json,csv,random,tempfile
import gradio as gr, pandas as pd
from dti_core import *
from commitment_rule import commitment, EN_VERBS, AR_VERBS

DICT=load_dictionary()
def C_(): return compile_dictionary(DICT)
def validated(): return {k for k,v in DICT.items() if v.get('validated')}

# ------------------------------------------------------------------ tab 1
LIVE=[('The bank implemented an artificial intelligence credit-scoring system in 2024.','en'),
      ('طبّق البنك أنظمة تعتمد الذكاء الاصطناعي في تقييم مخاطر الائتمان.','ar'),
      ('The company has access to cloud services through a third-party provider.','en'),
      ('The company upgraded its ERP system and integrated it with a cloud platform.','en'),
      ('نولي أهمية كبيرة لتحليلات البيانات الضخمة في خدمة عملائنا.','ar'),
      ('The company owns 100% of Lightning Gate for Cloud Services.','en')]

def code_sentence(text,lang=None):
    lang=lang or detect_lang(text); C=C_()
    techs=screen(text,lang,C)
    if not techs: return {'language':lang,'screen':'no dictionary term','present':0,'technology':'none','tier':0,'subject_ok':'','verb_from_list':'','verb':''}
    val=[t for t in techs if t in validated()]; new=[t for t in techs if t not in validated()]
    p=model_probs([text])[0] if val else None
    present=(p is not None and p>=THRESHOLD) or bool(new)
    tl=(val if (p is not None and p>=THRESHOLD) else [])+new
    c=commitment(text,lang) if present else None
    return {'language':lang,'screen':';'.join(techs),'model_prob':None if p is None else round(p,3),'present':int(present),
            'technology':('none' if not tl else (tl[0] if len(tl)==1 else 'multiple'))+(' (dictionary mode, unvalidated)' if new else ''),
            'subject_ok':c['subject_ok'] if c else '','verb_from_list':c['verb_from_list'] if c else '','verb':(c['verb'] or '') if c else '','tier':c['tier'] if c else 0}

def live_table():
    rows=[]
    for t,l in LIVE:
        r=code_sentence(t,l); rows.append([t,r['technology'],r['subject_ok'],r['verb_from_list'],r['verb'],r['tier']])
    return pd.DataFrame(rows,columns=['sentence','technology','subject_ok','verb_from_list','verb','tier'])

def code_files(files,lang_choice):
    if not files: return None,None,'Upload at least one file.'
    C=C_(); V=validated(); all_rows=[]; meas=[]; warn=[]
    for f in files:
        path=f if isinstance(f,str) else f.name; name=os.path.basename(path)
        try: sections=text_from_file(path)
        except Exception as e: warn.append(f'{name}: could not read ({e})'); continue
        # a full-filing JSON carries both languages: code each language as its own report
        groups={}
        if path.lower().endswith('.json') and any(sec.startswith(('en|','ar|')) for sec,_ in sections):
            for sec,t in sections: groups.setdefault(sec[:2],[]).append((sec[3:],t))
        else:
            full=' '.join(t for _,t in sections); groups[detect_lang(full) if lang_choice=='auto' else lang_choice]=sections
        for lang,secs in groups.items():
            if path.lower().endswith('.pdf') and lang=='ar': warn.append(f'{name}: Arabic PDF text extraction is not validated; check the sentence table before using the measures.')
            rows,m=code_document(secs,lang,C,V)
            for r in rows: all_rows.append({'file':name,'language':lang,**{k:r[k] for k in['section','text','technology','technologies','mode','prob','present','subject_ok','verb_from_list','verb','tier']}})
            meas.append({'file':name,'language':lang,**m})
    if not meas: return None,None,'\n'.join(warn) or 'Nothing coded.'
    sdf=pd.DataFrame(all_rows); mdf=pd.DataFrame(meas)
    out=os.path.join(tempfile.mkdtemp(),'dti_output.xlsx')
    with pd.ExcelWriter(out) as w: mdf.to_excel(w,sheet_name='report_measures',index=False); sdf.to_excel(w,sheet_name='sentences',index=False)
    msg=f'{len(meas)} report(s), {int(sdf["present"].sum()) if len(sdf) else 0} technology sentences, {int((sdf["tier"]==2).sum()) if len(sdf) else 0} tier 2.'
    if warn: msg+='\n'+'\n'.join(warn)
    return mdf,sdf,msg,out

# ------------------------------------------------------------------ tab 2
def dict_view(tech):
    v=DICT[tech]; return v['description'],v['terms']['en'] and [t['term'] for t in v['terms']['en']] or [], [t['term'] for t in v['terms']['ar']], v['examples']['tier2'], v['examples']['tier1'], 'validated' if v.get('validated') else 'unvalidated (dictionary mode)'
def dict_save(tech,desc,en_terms,ar_terms,ex2,ex1):
    v=DICT[tech]; v['description']=desc
    for lang,terms in(('en',en_terms),('ar',ar_terms)):
        old={t['term']:t for t in v['terms'][lang]}
        v['terms'][lang]=[old.get(x,{'term':x,'rule':'acronym' if (x.isupper() and len(x)<=5) else 'substring'}) for x in terms if x.strip()]
    v['examples']={'tier2':ex2,'tier1':ex1}; save_dictionary(DICT)
    return f'Saved {tech}: {len(v["terms"]["en"])} EN terms, {len(v["terms"]["ar"])} AR terms. Active in screening immediately.'
def dict_add(name,desc,en_terms,ar_terms,ex2,ex1):
    name=name.strip()
    if not name or name in DICT: return 'Give a new technology name.',gr.update()
    DICT[name]={'description':desc,'validated':False,'terms':{'en':[{'term':x.strip(),'rule':'substring'} for x in en_terms.split(',') if x.strip()],'ar':[{'term':x.strip(),'rule':'substring'} for x in ar_terms.split(',') if x.strip()]},'examples':{'tier2':ex2,'tier1':ex1}}
    save_dictionary(DICT)
    return f'Added {name} in dictionary mode (unvalidated). Use "Validate" to estimate its precision on your own reports.',gr.update(choices=list(DICT.keys()),value=name)
def dict_download():
    p=os.path.join(tempfile.mkdtemp(),'dictionary.json'); save_dictionary(DICT,p); return p
def dict_upload(f):
    global DICT; DICT=json.load(open(f.name if hasattr(f,'name') else f,encoding='utf-8')); save_dictionary(DICT)
    return f'Loaded dictionary with {len(DICT)} technologies.',gr.update(choices=list(DICT.keys()),value=list(DICT.keys())[0])

def validate_sample(tech,files,n=50):
    """draw up to n screen hits of one technology from the uploaded reports for hand coding"""
    if not files: return None,'Upload reports first (tab 1 files are not shared; upload here).'
    C=C_(); hits=[]
    for f in files:
        path=f if isinstance(f,str) else f.name
        try: sections=text_from_file(path)
        except Exception: continue
        lang=detect_lang(' '.join(t for _,t in sections))
        for sec,t in sections:
            for s in split_sentences(t,lang):
                if tech in screen(s,lang,C): hits.append([os.path.basename(path),lang,s,''])
    random.seed(0); random.shuffle(hits); hits=hits[:n]
    if not hits: return None,f'No sentences hit the {tech} dictionary in these files.'
    return pd.DataFrame(hits,columns=['file','language','sentence','correct? (1/0)']),f'{len(hits)} sentences drawn. Fill the last column with 1 (true mention) or 0, then press Compute precision.'
def validate_compute(df):
    if df is None or len(df)==0: return 'Nothing to compute.'
    col=df.iloc[:,-1].astype(str).str.strip(); done=col.isin(['0','1'])
    if done.sum()==0: return 'Fill the last column with 1 or 0 first.'
    prec=(col[done]=='1').mean()
    return f'Dictionary precision for this technology on your reports: {prec:.2f} ({int(done.sum())} coded). Below 0.60 means the term list needs tightening before use.'

# ------------------------------------------------------------------ tab 3
REL=pd.DataFrame([
 ['Round 1 (development)','300 sentences','commitment 0.282','superseded: rule v3 written after this round'],
 ['Calibration session','30 sentences, two coders, discussed','commitment 0.777, agreement 86.7%','sub-rules f1 to f6 written here'],
 ['Round 2 (development)','300 sentences','commitment 0.444, technology 0.532','six technology definitions written after this round'],
 ['Round 3 (independent, unseen)','100 sentences, two coders','binary 0.851 [0.734, 0.952]; technology nine-class 0.671 [0.552, 0.778]; commitment 0.698 [0.575, 0.816]','the reliability figures reported for the codebook'],
 ['Arabic rule check','50 Arabic sentences, two coders','commitment 0.865; subject_ok 0.831; verb_from_list 0.839','sub-rules f7, f8'],
 ['Rule script vs coders (development)','50 AR + 34 EN/AR','commitment 0.73 / 0.70 (AR 50); 0.71 vs coder A (EN 21)','script adjusted on these; clean test pending on 100 fresh sentences']],
 columns=['stage','sample','Cohen kappa (95% CI)','role'])
MODEL=pd.DataFrame([
 ['English, 26 held-out firms',319,39,'0.659 [0.53, 0.77]','0.691 [0.56, 0.81]','0.614 [0.50, 0.71]','0.618 [0.47, 0.74]'],
 ['Arabic, 27 held-out firms',333,28,'0.787 [0.66, 0.89]','0.814 [0.69, 0.91]','0.533 [0.41, 0.65]','0.647 [0.51, 0.77]']],
 columns=['test set','n','positives','model F1','hybrid F1','dictionary F1','LLM zero-shot F1'])
RULES=[('Tier 2 needs both','the reporting firm or one of its units is the subject, and a verb from the closed list acts on a technology term. Otherwise tier 1.'),
 ('Closed verb list, English',', '.join(EN_VERBS.keys())),('Closed verb list, Arabic',', '.join(k for k in AR_VERBS.keys() if k!='ب+مصدر')+' (and the ب+masdar form: باعتماد، بتطبيق ...)'),
 ('f1','a listed verb counts in participial or circumstantial form (by leveraging, باعتماد) when it acts on the technology'),
 ('f2','a nominalisation is not a verb: implementation, تطبيق alone = tier 1'),
 ('f3','an implicit firm subject is accepted in a description of a service or activity the firm provides'),
 ('f4','a system, plan or tool as subject fails the subject condition'),
 ('f5','passive voice without an agent fails the subject condition'),
 ('f6','a listed verb whose object is outside the six technologies does not count'),
 ('f7','"the company\'s plans / strategy / vision" as grammatical subject fails the subject condition'),
 ('f8','"made progress", "continued its journey" are not on the list'),
 ('Company names','a technology word inside a proper company name is not a technology mention'),
 ('Commercial service','providing a technology as a service to customers, or owning a company that does, is not adoption in the reporting firm\'s operations')]

with gr.Blocks(title='DTI Coder') as demo:
    gr.Markdown('# DTI Coder\nBilingual (Arabic / English) measurement of Digital Technology Integration in annual-report narrative. Sentence-level: dictionary screen, fine-tuned XLM-RoBERTa presence model, dictionary technology label, auditable commitment rule.')
    with gr.Tab('1. Code reports'):
        gr.Markdown('Upload rendered XBRL pages (.html), plain text, or PDF (English PDFs only are validated). Every sentence that passes the dictionary screen is shown with the model decision and the two rule columns, so each code can be audited.')
        with gr.Row():
            files=gr.File(label='Reports',file_count='multiple',file_types=['.html','.htm','.txt','.pdf','.json'])
            lang=gr.Radio(['auto','en','ar'],value='auto',label='Language')
        btn=gr.Button('Code',variant='primary'); msg=gr.Textbox(label='Status',lines=2)
        meas=gr.Dataframe(label='Report measures (density per 10,000 words, diversity, tier-2 share, counts per technology)')
        sents=gr.Dataframe(label='Sentences (audit table)',wrap=True)
        dl=gr.File(label='Download Excel')
        btn.click(code_files,[files,lang],[meas,sents,msg,dl])
        gr.Markdown('### Try one sentence')
        with gr.Row():
            one=gr.Textbox(label='Sentence',lines=2); onel=gr.Radio(['auto','en','ar'],value='auto',label='Language')
        oneb=gr.Button('Code sentence'); oneo=gr.JSON(label='Result')
        oneb.click(lambda t,l: code_sentence(t,None if l=='auto' else l),[one,onel],oneo)
        gr.Markdown('### Live examples')
        gr.Dataframe(value=live_table,wrap=True,label='Six worked examples (recomputed from the current dictionary and rule)')
    with gr.Tab('2. Technology dictionary'):
        gr.Markdown('Each technology has an editable term list per language. Edits take effect in screening immediately. A technology you add runs in **dictionary mode**: the screen and the commitment rule apply, the presence model is bypassed, and results are flagged unvalidated until you check precision on your own reports.')
        sel=gr.Dropdown(list(DICT.keys()),value=list(DICT.keys())[0],label='Technology')
        desc=gr.Textbox(label='Description'); status=gr.Textbox(label='Status',interactive=False)
        with gr.Row():
            en=gr.Dropdown(label='English terms',multiselect=True,allow_custom_value=True,choices=[]); ar=gr.Dropdown(label='Arabic terms',multiselect=True,allow_custom_value=True,choices=[])
        with gr.Row():
            ex2=gr.Textbox(label='Example, tier 2'); ex1=gr.Textbox(label='Example, tier 1')
        save=gr.Button('Save changes',variant='primary'); smsg=gr.Textbox(label='')
        def _view(t):
            d,e,a,x2,x1,st=dict_view(t); return d,gr.update(choices=e,value=e),gr.update(choices=a,value=a),x2,x1,st
        sel.change(_view,sel,[desc,en,ar,ex2,ex1,status]); demo.load(_view,sel,[desc,en,ar,ex2,ex1,status])
        save.click(dict_save,[sel,desc,en,ar,ex2,ex1],smsg)
        with gr.Accordion('+ Add a new technology',open=False):
            nname=gr.Textbox(label='Name (e.g. FinTech, Quantum)'); ndesc=gr.Textbox(label='Description')
            nen=gr.Textbox(label='English terms, comma-separated',lines=2); nar=gr.Textbox(label='Arabic terms, comma-separated',lines=2)
            nex2=gr.Textbox(label='Example, tier 2'); nex1=gr.Textbox(label='Example, tier 1')
            addb=gr.Button('Add'); amsg=gr.Textbox(label='')
            addb.click(dict_add,[nname,ndesc,nen,nar,nex2,nex1],[amsg,sel])
        with gr.Accordion('Validate a technology on your reports',open=False):
            gr.Markdown('Draws up to 50 sentences that hit this technology\'s terms in the reports you upload here. Code each as 1 (a true mention) or 0, then compute precision.')
            vfiles=gr.File(label='Reports',file_count='multiple'); vb=gr.Button('Draw sample'); vmsg=gr.Textbox(label='')
            vdf=gr.Dataframe(interactive=True,wrap=True); vc=gr.Button('Compute precision'); vres=gr.Textbox(label='')
            vb.click(validate_sample,[sel,vfiles],[vdf,vmsg]); vc.click(validate_compute,vdf,vres)
        with gr.Row():
            ddl=gr.Button('Download dictionary.json'); dfile=gr.File(label=''); dup=gr.File(label='Load dictionary.json'); dmsg=gr.Textbox(label='')
        ddl.click(dict_download,None,dfile); dup.change(dict_upload,dup,[dmsg,sel])
    with gr.Tab('3. Reliability and rules'):
        gr.Markdown('### Human reliability, by stage'); gr.Dataframe(value=REL,wrap=True)
        gr.Markdown('### Model performance on held-out firms (no firm shared with training, either language; 95% bootstrap CI)'); gr.Dataframe(value=MODEL,wrap=True)
        gr.Markdown('### Commitment rule v3'); gr.Dataframe(value=pd.DataFrame(RULES,columns=['rule','statement']),wrap=True)
        gr.Markdown('Corpus: 912 XBRL annual reports, Amman Stock Exchange, publication years 2021 to 2026, 182 firms; 326 paired filings read in full (all ELRs, both languages). XBRL filing has been mandatory since ASE Circular 129 (20 December 2020).')
if __name__=='__main__': demo.launch(server_name='0.0.0.0',server_port=int(os.environ.get('PORT','7860')))
