# DTI sentence codebook (master v6, 2026-09-22)

DTI sentence coding, version 2 - with artifact and expanded level 3 | 2026-09-22 v6
Unit | the sentence, as filed, in the language shown
COLUMN: technology | which of the six the sentence refers to, or artifact/none
AI/ML, Big Data, Cloud, ERP, SAR, XBRL, multiple, none, artifact
multiple = two or more of the six are named in the same sentence
none = no technology of the six AND not an artifact
artifact = structural noise: boilerplate_xbrl, cv_certificate, job_title, staff_table, table_header
COLUMN: commitment | 0 to 3, highest tier sentence reaches - REVISED
0 none | no technology mentioned OR artifact
1 bare mention | term appears with no act attributed to firm
example: digital transformation is reshaping banking sector
2 operational claim | firm attributes use/implementation to itself, no figure/accounting anchor
example: we implemented ERP across branches
3 financial anchoring - REVISED | accounting line OR monetary amount attached to technology
3a accounting anchor | رُسملت برمجيات، أصول غير ملموسة تشمل أنظمة، تم إطفاء أنظمة، recognized as intangible
3b monetary amount | software JD 1.2m capitalised, systems amount includes..., PPE computers amount
a capital expenditure figure that states it includes systems counts as 3b
COLUMN: amount_flag | NEW: does sentence itself contain a number? TRUE/FALSE
TRUE | sentence contains JD, %, million, etc linked to tech
FALSE | no number in sentence
COLUMN: realisation | realised or forward
realised | completed act or figure recorded in fiscal year just ended
vague near past during the year we worked on developing is realised
forward | intention, plan, expectation, forecast
NA | when commitment is 0 OR technology=artifact/none
COLUMN: artifact_type | NEW: if technology=artifact, subtype
boilerplate_xbrl | Signatures included in PDF uploaded to XBRL system, couldn't be uploaded on XBRL system
cv_certificate | Certificate Artificial Intelligence 2020, degree, personal qualification
job_title | BI Manager, Middleware, Data Analytics role, AvP Ahli Labs
staff_table | training programs list containing XBRL, AI as course names, staff numbers
table_header | other table/list artifact
COLUMN: notes | free text
Rule | code what sentence says, not what firm probably means
Rule | screen columns are hint, never answer; screen positive can be artifact/none
Rule | deduplication: within same symbol+pub_date, keep first occurrence, log all ELRs in duplicate_elrs
Rule for v2 | artifact excluded from LLM training, counted separately as noise source in paper
Finding | Level 3b is near-zero in Jordanian narrative - rarity is result, Level 3a saves ratio denominator
Rule, 2026-09-22 | A technology word inside the proper name of a company (subsidiary, affiliate, counterparty) does not count as a technology mention. Ownership, audit fees, tax provisions and board seats at such a company = none or artifact.
Rule, 2026-09-22 | Providing a technology as a commercial service to external customers (or owning a company that provides it) is not adoption of that technology in the reporting firm operations. Adoption requires the reporting firm (or its consolidated unit) to use the technology in its own operations. Such sentences = none.

## Technology definitions (v1, 2026-09-21)

تعريفات التكنولوجيات الست | v1, 2026-09-21, مبنية على حالات الخلاف الفعلية في الجولة الثانية
قاعدة عامة | الجملة تُرمَّز بتكنولوجيا فقط إذا ذَكَرت اسمها أو اسم نظام أو أداة تنتمي إليها صراحةً. لا يُستنتج من السياق.
إن لم يُذكر اسم، فالقيمة none مهما بدا الموضوع تقنياً.
AI/ML يدخل | الذكاء الاصطناعي، التعلم الآلي، التعلم العميق، الشبكات العصبية، الذكاء الاصطناعي التوليدي، معالجة اللغة الطبيعية، الروبوتات البرمجية RPA، روبوت المحادثة chatbot، المساعد الذكي.
AI/ML يخرج | ذكر AI داخل اسم دورة تدريبية أو شهادة أو مؤهل شخص = artifact لا AI/ML.
الرقمنة والتحول الرقمي وحدهما بلا ذكر AI = none.
حالة حدية محسومة: خطة للتحول الرقمي وتطبيقات الذكاء الاصطناعي = AI/ML (ذُكر الاسم صراحةً).
Big Data يدخل | البيانات الضخمة، تحليلات البيانات، data analytics، ذكاء الأعمال BI، مستودع البيانات، بحيرة البيانات data lake، النمذجة التنبؤية.
Big Data يخرج | تحليل بيانات تاريخية لأغراض محاسبية مثل مخصصات IFRS 9 = none، لأنه إجراء محاسبي لا تقنية.
ذكر BI داخل مسمى وظيفي = artifact.
Cloud يدخل | الحوسبة السحابية، السحابة، SaaS، PaaS، IaaS، الاستضافة السحابية، مزود خدمة سحابية مسمى.
Cloud يخرج | مجرد ذكر خوادم أو مراكز بيانات بلا صفة سحابية = none.
ERP يدخل | تخطيط موارد المؤسسة، SAP، Oracle ERP، Microsoft Dynamics، النظام المصرفي الأساسي core banking، أنظمة متكاملة مسماة، واجهات برمجة التطبيقات API حين تربط أنظمة المؤسسة.
ERP يخرج | ذكر نظام بلا تسمية ولا وصف تكامل = none.
حالة حدية محسومة: implementation of the SAP integrated information system = ERP.
SAR يدخل | الأرشفة الإلكترونية، إدارة المحتوى المؤسسي ECM، إدارة الوثائق الرقمية، التوقيع الإلكتروني، أتمتة سير العمل، التقارير الآلية.
SAR يخرج | حفظ الوثائق الورقية ومصفوفة السجلات وفترات الاحتفاظ بلا ذكر نظام إلكتروني = none.
حالة حدية محسومة: the institutional content system includes electronic archiving = SAR.
XBRL يدخل | XBRL، لغة تقارير الأعمال الموسعة، الوسم الرقمي للقوائم المالية، نظام الإفصاح الإلكتروني للهيئة حين يكون موضوع الجملة هو التقرير الرقمي نفسه.
XBRL يخرج | إقرارات المجلس وتوقيعاته التي تذكر رفع الملف على نظام XBRL = artifact بنوع boilerplate_xbrl.
القاعدة الفاصلة: إن كان ذكر XBRL وصفاً لإجراء الرفع أو التوقيع فهو artifact، وإن كان وصفاً لتبني الشركة للوسم الرقمي فهو XBRL.
multiple | تُستعمل فقط حين تُذكر تكنولوجيتان أو أكثر من الست صراحةً في نفس الجملة.
artifact | النص ليس إفصاحاً عن تبني: سيرة ذاتية، شهادة، مؤهل، مسمى وظيفي، جدول موظفين أو دورات، هيكل تنظيمي، برنامج أكاديمي، بويلربليت نظام الرفع.
artifact تسبق التكنولوجيا: إن انطبق الوصفان فالقيمة artifact.
none | لا اسم تكنولوجيا مذكور، أو المذكور خارج الست.

## Commitment rule v3 with sub-rules f1 to f8

قاعدة الحد بين المرتبة 1 والمرتبة 2 | v3, 2026-09-21
المرتبة 2 | تتحقق بشرطين معاً، وإلا فالجملة مرتبة 1
الشرط الأول: الفاعل | الفاعل هو الشركة المُبلِّغة أو وحدة منها: البنك، الشركة، المجموعة، الدائرة، الإدارة، قطاع أو وحدة أعمال مسماة، أو ضمير المتكلم (نحن، قمنا).
لا يتحقق الشرط إذا كان الفاعل هو التكنولوجيا نفسها، أو السوق، أو القطاع، أو جهة خارجية.
مثال لا يتحقق: التحليلات المتقدمة تهدف إلى ضمان حصول العملاء على محتوى مفيد.
الشرط الثاني: الفعل | فعل متعدٍ من القائمة المغلقة أدناه، واقع مباشرة على التكنولوجيا أو على نظام يقوم عليها.
القائمة المغلقة، عربي | طبّق، استخدم، اعتمد، اعتمد على، أطلق، دمج، نفّذ، طوّر، بنى، حدّث، رقّى، أتمت، استثمر في، وظّف، شغّل، ركّز على، يستند إلى
القائمة المغلقة، إنجليزي | implemented, deployed, adopted, launched, integrated, utilised, used, developed, built, upgraded, automated, rolled out, invested in, leveraged, relies on, evolved, focused on, operates, maintains
الزمن لا يغيّر المرتبة | فعل من القائمة في صيغة الوعد يبقى مرتبة 2، ويُسجَّل الزمن في عمود realisation بقيمة forward.
مثال: سنعزز الكفاءة التشغيلية باعتماد أحدث حلول الذكاء الاصطناعي = 2 + forward.
هذا الفصل إلزامي: المرتبة تقيس نوع الادعاء، وrealisation تقيس زمنه.
أمثلة محسومة | 1 = نولي أهمية كبيرة للذكاء الاصطناعي (فاعل موجود، فعل ليس في القائمة)
1 = التحول الرقمي يعيد تشكيل القطاع (لا فاعل شركة)
1 = رؤيتنا تكتمل بالذكاء الاصطناعي (لا فعل من القائمة)
2 = طبّق البنك أنظمة تعتمد الذكاء الاصطناعي
2 = ركّزت وحدة الأعمال المصرفية للأفراد على الرقمنة
عند الشك | إن تحقق الشرطان فهي 2، وإلا فهي 1. لا تجتهد خارج القائمة، واكتب الحالة في notes.
قواعد فرعية من جلسة التثبيت | 30 جملة، كابا commitment = 0.777، اتفاق 86.7%، 2026-09-21
ف1 | الفعل من القائمة يُحتسب ولو جاء حالاً أو ظرفاً، ما دام واقعاً على التكنولوجيا.
مثال: by leveraging advanced analytics = 2. مثال: by adopting AI tools = 2.
ف2 | المصدر الاسمي ليس فعلاً. implementation أو تطبيق كاسم وحده = 1.
ف3 | الفاعل الضمني مقبول في وصف خدمة أو نشاط تقدمه الشركة.
ف4 | الفاعل إذا كان نظاماً أو خطة أو أداة، لا الشركة، فالشرط الأول لا يتحقق = 1.
مثال: IT asset management system يقوم بـ ... الفاعل نظام. مثال: training plan يهدف إلى ...
ف5 | المبني للمجهول بلا فاعل واضح لا يحقق الشرط الأول. was upgraded وحدها = 1.
ف6 | الفعل من القائمة إذا كان مفعوله خارج التكنولوجيات الست لا يُحتسب.
مثال: أطلقنا خدمات الجيل الخامس = ليست من الست، فلا تُرمَّز تكنولوجيا أصلاً.
قواعد فرعية من فحص العربية | 50 جملة، كابا 0.865، 2026-09-22
ف7 | صيغة "خطط الشركة" أو "استراتيجية الشركة" أو "رؤية الشركة" كفاعل نحوي لا تحقق شرط الفاعل. الفاعل هو الخطة لا الشركة = 1.
ف8 | "أحرز تقدماً" و"واصل مسيرته" ليست من القائمة المغلقة. إن لم يرد فعل من القائمة في الجملة نفسها = 1.