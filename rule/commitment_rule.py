"""Commitment rule v3.1 (tier 1 vs tier 2) as a deterministic, auditable function.
v3.1 (2026-09-23), frozen before the clean test with coder B: object window = whole clause up to 30 words, technology terms of both
languages accepted as object (English product names inside Arabic text); a nominalisation that governs the technology (implementation of X,
بتطبيق / لتوظيف / واستخدام X, سنواصل الاستثمار في X) counts as the verb condition when a firm subject is present (extension of f1);
a bare nominalisation as sentence subject still fails (f2); passive without agent still fails (f5).
Input: a sentence already judged to mention one of the six technologies, and its language.
Output: subject_ok, verb_from_list, verb, tier (2 if both conditions hold, else 1).

Condition 1 (subject): the reporting firm or one of its units is the grammatical subject of the verb
  (firm noun or first-person marker before the verb in the same clause; implicit firm subject in a
  participial or imperative opening is accepted, f3). Fails on passive without agent (f5), and when the
  clause subject is a plan / strategy / vision / system / tool / technology / market (f4, f7).
Condition 2 (verb): a verb from the closed list, in verbal form (nominalisations do not count, f2;
  a circumstantial form such as "by leveraging" or Arabic "ب+مصدر" counts, f1), whose object is a
  technology term: a dictionary term of one of the six technologies occurs within OBJ_WINDOW words
  after the verb, in the same clause (f6).
"""
import re,unicodedata,csv,os
OBJ_WINDOW=30
_DICT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'DTI_dictionary_v3_terms.csv')

# ---------- normalisation (same as the screen) ----------
PROTECT={'الالي','الاليه','اليا','الى','الي'}
AR_IND=str.maketrans('٠١٢٣٤٥٦٧٨٩','0123456789')
def norm(s):
    s=unicodedata.normalize('NFKC',s).translate(AR_IND)
    s=re.sub(r'[ً-ْـ]','',s); s=re.sub('[أإآ]','ا',s).replace('ة','ه').replace('ى','ي').lower()
    s=re.sub(r'[-/]',' ',s); s=re.sub(r'[^\w؀-ۿ]+',' ',s)
    return ' '.join(w[2:] if (w.startswith('ال') and len(w)>=5 and w not in PROTECT) else w for w in s.split())

# ---------- technology terms ----------
TERMS={'en':[],'ar':[]}
for t in csv.DictReader(open(_DICT,encoding='utf-8-sig')):
    term=norm(t['term_norm_v3'] or t['term'])
    if term: TERMS[t['lang']].append(term)
TERMS['en']+= ['ai','ml','bi','erp','sap','xbrl','rpa','saas','paas','iaas']   # acronyms (already screened upstream)
TERMS['ar']+= ['ذكاء اصطناعي','تعلم الي','بيانات ضخمه','حوسبه سحابيه','سحابه','ارشفه الكترونيه','xbrl','erp','sap']

def tech_positions(words,lang):
    """indices of words that start a technology term in the normalised word list"""
    pos=set(); joined=' '.join(words)
    for term in TERMS[lang]:
        tw=term.split(); L=len(tw)
        for i in range(len(words)-L+1):
            if words[i:i+L]==tw: pos.add(i)
    return pos

CLAUSE_BREAK=re.compile(r'[.;:!؟?؛]|\s[-–—]\s')

# ---------- English ----------
EN_VERBS={
 'implement':r'implement(?:ed|s|ing)?','deploy':r'deploy(?:ed|s|ing)?','adopt':r'adopt(?:ed|s|ing)?','launch':r'launch(?:ed|es|ing)?',
 'integrate':r'integrat(?:e|ed|es|ing)','utilise':r'utili[sz](?:e|ed|es|ing)','use':r'us(?:e|ed|es|ing)','develop':r'develop(?:ed|s|ing)?',
 'build':r'(?:build|builds|building|built)','upgrade':r'upgrad(?:e|ed|es|ing)','automate':r'automat(?:e|ed|es|ing)','roll out':r'roll(?:ed|s|ing)?\s+out',
 'invest in':r'invest(?:ed|s|ing)?\s+in','leverage':r'leverag(?:e|ed|es|ing)','rely on':r'(?:rely|relies|relied|relying)\s+(?:on|upon)',
 'evolve':r'evolv(?:e|ed|es|ing)','focus on':r'focus(?:ed|es|ing)?\s+on','operate':r'operat(?:e|ed|es|ing)','maintain':r'maintain(?:ed|s|ing)?'}
EN_NOMINAL={'implementation of':r'implementation\s+of','deployment of':r'deployment\s+of','adoption of':r'adoption\s+of','launch of':r'launch(?:ing)?\s+of','integration of':r'integration\s+of',
 'use of':r'(?:use|usage|utili[sz]ation)\s+of','development of':r'development\s+of','automation of':r'automation\s+of','investment in':r'investments?\s+in','upgrade of':r'upgrad(?:e|ing)\s+of','rollout of':r'roll-?out\s+of'}
EN_VERB_RE=re.compile(r'\b(?:'+'|'.join(f'(?P<{k.replace(" ","_")}>{v})' for k,v in list(EN_VERBS.items())+list(EN_NOMINAL.items()))+r')\b',re.I)
EN_FIRM=re.compile(r'\b(?:we|our|us|the (?:company|bank|group|corporation|firm|university|institution|department|division|unit|team|management|board)|'
                   r'[A-Z][A-Za-z&\-]+ (?:Bank|Company|Group|Holding|Corporation|University|Co\.?|PLC|JSC))',re.I)
EN_PASSIVE=re.compile(r'\b(?:was|were|is|are|been|being|be)\s+(?:\w+ly\s+)?(?:implemented|deployed|adopted|launched|integrated|utili[sz]ed|used|developed|built|upgraded|automated|rolled out|leveraged|operated|maintained)\b',re.I)
EN_BAD_SUBJECT=re.compile(r'^\s*(?:the\s+|our\s+|this\s+|these\s+|its\s+)?(?:\w+\s+){0,3}?(?:plan|plans|strategy|vision|system|systems|platform|tool|tools|solution|application|technology|technologies|market|sector|industry|project|table|guides?)\b',re.I)
EN_IMPLICIT=re.compile(r'^\s*(?:by\s+)?(?:implement|deploy|adopt|launch|integrat|utili[sz]|us|develop|build|upgrad|automat|roll|invest|leverag|rely|focus|operat|maintain)(?:ed|s|es|ing)?\b(?!\s+of\b)',re.I)
EN_NOMINAL_BARE=re.compile(r'^\s*(?:the\s+)?(?:implementation|deployment|adoption|launch|integration|use|usage|utili[sz]ation|development|automation|investment|upgrade|roll-?out)\s+of\b',re.I)

def _clause(text,start):
    """clause containing char offset start: split on clause breaks"""
    left=0
    for m in CLAUSE_BREAK.finditer(text):
        if m.end()<=start: left=m.end()
        else: return text[left:m.start()], start-left
    return text[left:], start-left

def en_rule(text):
    t=text.strip(); best=None
    for m in EN_VERB_RE.finditer(t):
        verb=next(k for k,v in m.groupdict().items() if v)
        clause,off=_clause(t,m.start())
        after=clause[off+len(m.group(0)):]
        words=norm(after).split()[:OBJ_WINDOW]
        obj=bool(tech_positions(words,'en')) or bool(tech_positions(words,'ar'))
        before=clause[:off]
        firm=bool(EN_FIRM.search(before)) or bool(EN_IMPLICIT.match(clause))
        passive=bool(EN_PASSIVE.search(clause)) and not re.search(r'\bby (?:the )?(?:company|bank|group|us|our)\b',clause,re.I)
        bad=(bool(EN_BAD_SUBJECT.match(before)) and not re.match(r'^\s*(?:we|our|the (?:company|bank|group))\b',before,re.I)) or bool(EN_NOMINAL_BARE.match(clause))
        # 'this includes the implementation of X' : the firm is the implicit subject of an inventory sentence (f3) when no other subject noun precedes
        if not firm and re.match(r'^\s*(?:this|these|it)\s+(?:includes?|included|comprises?|involves?|covers?)\b',before,re.I): firm=True
        subj=firm and not passive and not bad
        cand=(subj and obj, obj, subj, verb)
        if best is None or cand>best: best=cand
    if best is None:   # no listed verb: subject judged on the whole sentence, for the audit column
        firm=bool(EN_FIRM.search(t)) or bool(EN_IMPLICIT.match(t)); passive=bool(EN_PASSIVE.search(t)); bad=bool(EN_BAD_SUBJECT.match(t))
        return (firm and not passive and not bad), False, None
    tier2,obj,subj,verb=best
    return subj, obj, verb   # verb_from_list is True only when the verb has a technology object

# ---------- Arabic ----------
PRE=r'(?:و|ف)?(?:س)?'
AR_VERBS={
 'طبق':PRE+r'(?:طبق|تطبق|يطبق|نطبق|طبقت|طبقنا|طبقوا)','استخدم':PRE+r'(?:استخدم|تستخدم|يستخدم|نستخدم|استخدمت|استخدمنا|استخدموا)',
 'اعتمد':PRE+r'(?:اعتمد|تعتمد|يعتمد|نعتمد|اعتمدت|اعتمدنا|اعتمدوا)','اطلق':PRE+r'(?:اطلق|تطلق|يطلق|نطلق|اطلقت|اطلقنا|اطلقوا)',
 'دمج':PRE+r'(?:دمج|تدمج|يدمج|ندمج|دمجت|دمجنا)','نفذ':PRE+r'(?:نفذ|تنفذ|ينفذ|ننفذ|نفذت|نفذنا)','طور':PRE+r'(?:طور|تطور|يطور|نطور|طورت|طورنا)',
 'بنى':PRE+r'(?:بني|تبني|يبني|نبني|بنت|بنينا)','حدث':PRE+r'(?:حدث|تحدث|يحدث|نحدث|حدثت|حدثنا)','رقى':PRE+r'(?:رقي|ترقي|يرقي|نرقي|رقت)',
 'اتمت':PRE+r'(?:اتمت|تؤتمت|يؤتمت|نؤتمت|اتمتت)','استثمر في':PRE+r'(?:استثمر|تستثمر|يستثمر|نستثمر|استثمرت|استثمرنا)(?:\s+\S+){0,6}?\s+في',
 'وظف':PRE+r'(?:وظف|توظف|يوظف|نوظف|وظفت|وظفنا)','شغل':PRE+r'(?:شغل|تشغل|يشغل|نشغل|شغلت|شغلنا)',
 'ركز على':PRE+r'(?:ركز|تركز|يركز|نركز|ركزت|ركزنا)(?:\s+\S+){0,6}?\s+علي','استند الى':PRE+r'(?:استند|تستند|يستند|نستند|استندت)(?:\s+\S+){0,6}?\s+الي',
 'ب+مصدر':r'(?:ب|ل|و|وب|ول|عبر\s+|من\s+خلال\s+|علي\s+|في\s+|الي\s+)(?:اعتماد|تطبيق|استخدام|اطلاق|دمج|تنفيذ|تطوير|بناء|تحديث|ترقيه|اتمته|توظيف|تشغيل|الاستثمار في|الاعتماد علي|التركيز علي)|(?:و|ف)?(?:ن|س|سن)?(?:واصل|تواصل|يواصل|نواصل|واصلت|واصلنا|ستواصل|سنواصل|بدا|بدات|بدانا|نبدا|تبدا|يبدا)\s+(?:ب|في\s+)?(?:الاستثمار في|الاعتماد علي|التركيز علي|اعتماد|تطبيق|استخدام|اطلاق|دمج|تنفيذ|تطوير|بناء|تحديث|توظيف|تشغيل)'}
AR_VERB_RE=re.compile(r'(?<![\w])(?:'+'|'.join(f'(?P<v{i}>{v})' for i,v in enumerate(AR_VERBS.values()))+r')(?![\w])')
AR_KEYS=list(AR_VERBS.keys())
AR_FIRM=re.compile(r'(?:البنك|الشركه|المجموعه|الدائره|الاداره|المصرف|الجامعه|المؤسسه|قطاع الاعمال|وحده الاعمال|وحده اعمال|فريق|نحن|قمنا|قام|قامت)')
AR_WE=re.compile(r'(?<![\w])(?:و|ف)?(?:س)?ن(?:طبق|ستخدم|عتمد|طلق|دمج|نفذ|طور|بني|حدث|ؤتمت|ستثمر|وظف|شغل|ركز|ستند|قوم|عمل|واصل|سعي|عزز|ولي|هدف|حرص|لتزم)|(?<![\w])(?:و|ف)?سن\w{2,}|\w+نا(?![\w])')
AR_PASSIVE=re.compile(r'(?<![\w])(?:و)?تم(?:ت)?\s+(?:اعتماد|تطبيق|استخدام|اطلاق|دمج|تنفيذ|تطوير|بناء|تحديث|ترقيه|اتمته|توظيف|تشغيل|شراء)')
AR_BAD_SUBJECT=re.compile(r'(?:^|[،,]\s*)(?:و|ف)?(?:كما\s+)?(?:ان\s+)?(?:خطه|خطط|استراتيجيه|رؤيه|نظام|انظمه|منصه|اداه|ادله|التكنولوجيا|التقنيه|السوق|القطاع|الصناعه|مشروع|مشاريع)\s*$')
def ar_prep(s):
    s=unicodedata.normalize('NFKC',s); s=re.sub(r'[ً-ْـ]','',s); s=re.sub('[إأآا]','ا',s); return s.replace('ى','ي').replace('ة','ه')

def ar_rule(text):
    t=ar_prep(text.strip()); best=None
    for m in AR_VERB_RE.finditer(t):
        verb=next(k for i,k in enumerate(AR_KEYS) if m.group(f'v{i}'))
        clause,off=_clause(t,m.start())
        after=clause[off+len(m.group(0)):]
        words=norm(after).split()[:OBJ_WINDOW]
        obj=bool(tech_positions(words,'ar')) or bool(tech_positions(words,'en'))
        before=clause[:off]
        # subject = firm noun before the verb in the clause, or first-person / firm-suffix on the verb itself
        firm=bool(AR_FIRM.search(before)) or bool(AR_WE.search(before)) or bool(AR_WE.match(m.group(0))) or bool(AR_FIRM.search(m.group(0))) or bool(AR_FIRM.search(after[:40]))  # VSO: verb then firm subject
        passive=bool(AR_PASSIVE.search(clause)) and not re.search(r'من قبل (?:البنك|الشركه|المجموعه)',clause)
        bad=bool(AR_BAD_SUBJECT.search(before.strip()))
        subj=firm and not passive and not bad
        cand=(subj and obj, obj, subj, verb)
        if best is None or cand>best: best=cand
    if best is None:
        firm=bool(AR_FIRM.search(t)) or bool(AR_WE.search(t)); passive=bool(AR_PASSIVE.search(t)); bad=bool(AR_BAD_SUBJECT.search(t.split('،')[0].strip()))
        return (firm and not passive and not bad), False, None
    tier2,obj,subj,verb=best
    return subj, obj, verb

def commitment(text,lang):
    s,v,verb=(ar_rule if lang=='ar' else en_rule)(text)
    return {'subject_ok':bool(s),'verb_from_list':bool(v),'verb':verb,'tier':2 if (s and v) else 1}
