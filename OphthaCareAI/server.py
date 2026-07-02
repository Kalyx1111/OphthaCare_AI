"""
OphthaCare AI - Production Backend Server v1.0
Ophthalmology Health Intelligence Platform
"""
import os, sys, json, uuid, time, hashlib, logging, datetime, argparse
from pathlib import Path

try:
    from flask import Flask, request, jsonify, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("[FATAL] Flask not installed. Run REPAIR_AND_RECOVER.bat"); sys.exit(1)

try:
    import requests as req_lib
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    import fitz; FITZ_OK = True
except ImportError:
    FITZ_OK = False

try:
    from PIL import Image; PIL_OK = True
except ImportError:
    PIL_OK = False

sys.path.insert(0, str(Path(__file__).parent / "modules"))
try:
    import ai_providers; AI_PROVIDERS_OK = True
except ImportError:
    AI_PROVIDERS_OK = False

BASE_DIR    = Path(__file__).parent.resolve()
UPLOAD_DIR  = BASE_DIR / "uploads"
LOGS_DIR    = BASE_DIR / "logs"
DATA_DIR    = BASE_DIR / "data"
STATIC_DIR  = BASE_DIR / "static"
REPORTS_DIR = BASE_DIR / "reports_db"

for d in [UPLOAD_DIR, LOGS_DIR, DATA_DIR, STATIC_DIR, REPORTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

PORT    = int(os.environ.get("OPHTHACARE_PORT", 5085))
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DEFAULT_PROVIDER_KEYS = ai_providers.get_env_keys() if AI_PROVIDERS_OK else {}
VERSION = "1.0.0"

DISCLAIMER = (
    "WARNING - AI RESEARCH DISCLAIMER: All output is AI-generated from published "
    "ophthalmology literature (AAO, RCOphth, WHO, NICE, AIOS, PubMed). For "
    "educational research only. NOT medical advice. ALWAYS consult a qualified "
    "ophthalmologist. EYE EMERGENCY (sudden vision loss, chemical injury, penetrating "
    "injury, acute red painful eye, flashes/floaters with curtain): "
    "Call 112 (India) / 999 (UK) / 911 (US) immediately."
)

log_file = LOGS_DIR / f"server_{datetime.date.today()}.log"
logging.basicConfig(level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)])
log = logging.getLogger("OphthaCareAI")

app = Flask(__name__, static_folder=str(STATIC_DIR))
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024
CORS(app, origins="*")

_RATE_STORE = {}

def _get_client_id():
    return hashlib.sha256((request.remote_addr or '127.0.0.1').encode()).hexdigest()[:16]

def rate_limit_check():
    cid = _get_client_id(); now = time.time()
    _RATE_STORE.setdefault(cid, [])
    _RATE_STORE[cid] = [t for t in _RATE_STORE[cid] if now - t < 60]
    if len(_RATE_STORE[cid]) >= 30: return False
    _RATE_STORE[cid].append(now); return True

def sanitise_api_key(key):
    if not key or not isinstance(key, str): return ''
    key = key.strip()
    if len(key) > 512: return ''
    s = ''.join(c for c in key if 0x21 <= ord(c) <= 0x7E)
    return s if len(s) >= 10 else ''

def validate_provider(p):
    return p.lower() if p and p.lower() in {'anthropic','openai','gemini','grok','deepseek'} else 'anthropic'

# ===== OPHTHALMOLOGY KNOWLEDGE BASE =====
KNOWLEDGE = {
    "refractive_errors": {
        "name": "Refractive Errors",
        "myopia": "Short-sightedness - distant objects blurred. Eye too long or cornea too curved. Corrected with concave (minus) lenses. Global myopia epidemic - linked to reduced outdoor time and increased near work. Myopia control options: low-dose atropine 0.01-0.05% nightly, orthokeratology, DIMS/HAL spectacle lenses, multifocal soft contact lenses. 2+ hours outdoor time daily has good evidence for reducing onset and progression in children.",
        "hyperopia": "Long-sightedness - near objects blurred (severe: all distances). Eye too short or cornea too flat. Corrected with convex (plus) lenses. Common in young children (physiological), often reduces with growth.",
        "astigmatism": "Irregular corneal or lens curvature causing blur at all distances. Corrected with cylindrical lenses matched to the axis. Often coexists with myopia or hyperopia.",
        "presbyopia": "Age-related loss of near focusing ability (accommodative amplitude) due to lens stiffening, typically from the early-to-mid 40s. Managed with reading glasses, bifocals, varifocals, or near addition to contact lens prescription.",
        "investigations": "Visual acuity (Snellen/LogMAR), refraction (subjective and objective), cycloplegic refraction in children (cyclopentolate 1% to relax accommodation), corneal topography for irregular astigmatism.",
    },
    "cataract": {
        "name": "Cataract",
        "definition": "Clouding of the eye natural crystalline lens causing progressive blurred, hazy or dim vision. Leading cause of reversible blindness worldwide. Most commonly age-related but can be congenital, traumatic, secondary, or drug-induced (long-term corticosteroids).",
        "symptoms": "Gradual painless blurring, glare/haloes around lights (especially at night), faded colour perception, frequent prescription changes, difficulty reading or recognising faces, second sight phenomenon (temporary near vision improvement early in nuclear cataract).",
        "types": "Nuclear sclerotic (central, most common), cortical (spoke-like opacities), posterior subcapsular (back of lens, disproportionate glare/near difficulty, associated with steroid use), congenital.",
        "management": "Phacoemulsification with intraocular lens (IOL) implantation - day case, local anaesthetic. IOL options: monofocal (single focal distance, glasses for near), multifocal/EDOF (reduce spectacle dependence, may cause haloes), toric (correct astigmatism). Posterior capsule opacification (PCO) is common months-years post-op - treated with quick outpatient YAG laser capsulotomy.",
    },
    "glaucoma": {
        "name": "Glaucoma",
        "definition": "Group of optic neuropathies causing progressive irreversible visual field loss, typically with raised IOP. Second leading cause of blindness globally. The silent thief of sight - often asymptomatic until significant damage.",
        "open_angle": "Primary Open-Angle Glaucoma (POAG) - most common type. Aqueous outflow impaired at trabecular meshwork despite open angle. Risk factors: raised IOP, age, family history (6x risk first-degree relative), African ancestry, myopia, thin cornea, diabetes.",
        "angle_closure": "Acute Angle-Closure Glaucoma - EMERGENCY. Drainage angle physically blocked. Severe eye pain, redness, blurred vision, haloes, nausea/vomiting, fixed mid-dilated pupil, hazy cornea. Requires immediate IOP-lowering treatment then laser peripheral iridotomy (LPI) to both eyes.",
        "investigations": "Goldmann applanation tonometry (IOP gold-standard), optic disc assessment (cup-to-disc ratio, neuroretinal rim), visual field testing (Humphrey 24-2 perimetry), OCT retinal nerve fibre layer (RNFL) and optic nerve head, gonioscopy (angle anatomy), pachymetry (central corneal thickness).",
        "management": "Goal: lower IOP to prevent progression. First-line: prostaglandin analogues (latanoprost 0.005% once nightly) or SLT laser. Also: beta-blockers (timolol - caution asthma/COPD/bradycardia), carbonic anhydrase inhibitors (dorzolamide), alpha agonists (brimonidine). Surgery: trabeculectomy, MIGS, tube shunts for medically uncontrolled disease. Lifelong monitoring essential.",
    },
    "retinal_disease": {
        "name": "Retinal Diseases",
        "amd": "Age-related Macular Degeneration - leading cause of central vision loss in adults over 50. Dry AMD (90%): drusen, gradual atrophy, no curative treatment, AREDS2 vitamins slow intermediate AMD progression. Wet AMD (10%, most severe): choroidal neovascularisation, sudden central distortion/vision loss - URGENT. Anti-VEGF injections (ranibizumab, aflibercept, faricimab, bevacizumab) can stabilise or improve vision if started promptly.",
        "diabetic_retinopathy": "Leading cause of blindness in working-age adults. Graded: non-proliferative DR (mild/moderate/severe), proliferative DR (neovascularisation - risk of vitreous haemorrhage/tractional detachment), diabetic macular oedema (central vision loss at any stage). Management: tight HbA1c and blood pressure control (most important), annual screening, anti-VEGF injections for DMO and PDR, pan-retinal laser for PDR, vitrectomy for complications.",
        "retinal_detachment": "EMERGENCY. Symptoms: sudden flashes, shower of new floaters, curtain/shadow across visual field. Rhegmatogenous most common - retinal tear allows fluid beneath retina. Risk factors: high myopia, prior cataract surgery, trauma. Treatment: vitrectomy, scleral buckle, or pneumatic retinopexy. Outcome strongly time-dependent - macula-on detachment is more urgent.",
        "retinal_vein_occlusion": "Central or branch RVO - sudden painless vision loss/blur. Associated with hypertension, diabetes, glaucoma. Anti-VEGF injections for macular oedema. Treat vascular risk factors. Monitor for neovascular glaucoma (ischaemic CRVO).",
        "retinal_artery_occlusion": "OPHTHALMIC EMERGENCY - stroke of the eye. Sudden profound painless vision loss. Cherry-red spot at macula. Urgent cardiovascular workup (carotid, cardiac). High stroke risk - TIA-equivalent.",
    },
    "cornea_external": {
        "name": "Cornea and External Eye Disease",
        "conjunctivitis": "Bacterial: purulent discharge, topical chloramphenicol. Viral: watery, bilateral, self-limiting, highly contagious, supportive care. Allergic: itching prominent, antihistamine/mast cell stabiliser drops.",
        "dry_eye": "Tear film instability - irritation, grittiness, burning, fluctuating vision, paradoxical watering. Managed with preservative-free artificial tears, warm compresses/lid hygiene, punctal plugs, topical cyclosporin for inflammatory dry eye.",
        "keratitis": "Bacterial (contact lens risk) - EMERGENCY, same-day assessment, intensive fluoroquinolone drops, corneal scrape for culture. Herpes simplex (dendritic ulcer) - topical/oral antivirals, AVOID steroids without specialist guidance. Acanthamoeba (water/contact lens) - intensive PHMB/propamidine, specialist management.",
        "chemical_injury": "TRUE EMERGENCY. Irrigate immediately with any available clean water for 20-30 minutes BEFORE seeking help. Check pH, continue until neutral. Alkali burns worse than acid. Urgent ophthalmology after irrigation.",
        "blepharitis": "Chronic lid margin inflammation - anterior (staphylococcal/seborrhoeic) or posterior (meibomian gland dysfunction). Warm compresses, lid massage, lid cleaning - chronic condition requiring ongoing maintenance.",
    },
    "uveitis": {
        "name": "Uveitis and Inflammatory Eye Disease",
        "definition": "Uveal tract inflammation. Classified: anterior (iritis/iridocyclitis - most common), intermediate, posterior, panuveitis. Causes: HLA-B27 conditions, JIA, sarcoidosis, infections, idiopathic.",
        "anterior_uveitis": "Pain, photophobia, circumcorneal redness, blurred vision, cells/flare in anterior chamber on slit-lamp. Associated with HLA-B27 disease (ankylosing spondylitis, reactive arthritis, IBD, psoriatic arthritis), JIA (often asymptomatic - screening essential).",
        "management": "Topical corticosteroids (prednisolone acetate) tapered gradually. Cycloplegic drops (cyclopentolate/atropine) for pain and synechiae prevention. Treat underlying systemic cause. Systemic immunosuppression for severe/recurrent/posterior disease. Monitor for complications: cataract, glaucoma, cystoid macular oedema.",
    },
    "neuro_ophthalmology": {
        "name": "Neuro-Ophthalmology",
        "optic_neuritis": "Subacute unilateral vision loss, pain on eye movement, reduced colour vision, RAPD. Strongly associated with multiple sclerosis. MRI brain/orbits with contrast key investigation. Most recover substantially without treatment; IV steroids speed recovery but do not change final outcome.",
        "papilloedema": "Bilateral optic disc swelling from raised intracranial pressure. Causes: idiopathic intracranial hypertension, space-occupying lesion, venous sinus thrombosis. Urgent neuroimaging required.",
        "giant_cell_arteritis": "EMERGENCY in over-50s. New headache, scalp tenderness, jaw claudication, any visual symptoms. Urgent ESR/CRP + immediate high-dose corticosteroids - do not wait for biopsy. Can cause sudden irreversible bilateral blindness.",
        "third_nerve_palsy": "Pupil-involving third nerve palsy (ptosis, down-and-out eye, dilated pupil) is a NEUROSURGICAL EMERGENCY - posterior communicating artery aneurysm until proven otherwise. Urgent CT/MR angiography.",
    },
    "ocular_emergency": {
        "name": "Ophthalmic Emergencies",
        "chemical_burn": "TRUE EMERGENCY - irrigate immediately with any available clean water 20-30 minutes BEFORE anything else. Do not stop to seek help first. Check pH, continue until neutral. Alkali burns worse (liquefactive necrosis, deeper penetration). Then urgent ophthalmology.",
        "penetrating_injury": "Do NOT press on eye. Do NOT remove embedded foreign body. Do NOT instil drops or ointment. Place rigid shield (not a pad). Urgent same-day eye casualty - risk of endophthalmitis and vision loss.",
        "acute_angle_closure": "Severe eye pain, redness, haloes, blurred vision, nausea, fixed mid-dilated pupil, hazy cornea. EMERGENCY. Immediate IOP-lowering then laser iridotomy both eyes.",
        "sudden_vision_loss": "Any sudden vision loss requires same-day ophthalmology assessment. Cause determines urgency and management.",
        "flashes_floaters_curtain": "Sudden shower of floaters + flashes + curtain/shadow = retinal detachment until proven otherwise. Same-day dilated fundus examination.",
    },
    "contact_lens_care": {
        "name": "Contact Lens Safety",
        "rules": "Always wash and dry hands. NEVER use tap water (Acanthamoeba risk). Replace lens case monthly with fresh solution (never top up). Do not sleep in lenses unless approved for extended wear. Do not swim/shower in reusable lenses.",
        "warning_signs": "Remove immediately and seek same-day assessment for: eye pain, increasing redness, significant photophobia, blurred vision, excessive watering. Microbial keratitis can progress rapidly.",
        "types": "Daily disposable (safest, no case needed), fortnightly/monthly (strict hygiene required), RGP (best optics, adaptation period), orthokeratology (overnight, myopia control), scleral (irregular corneas, severe dry eye).",
    },
}

def save_knowledge():
    with open(DATA_DIR / "ophtha_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(KNOWLEDGE, f, indent=2, ensure_ascii=False)

def load_sessions():
    sf = DATA_DIR / "sessions.json"
    if sf.exists():
        with open(sf) as f: return json.load(f)
    return {}

def save_session(sid, data):
    sessions = load_sessions()
    sessions[sid] = {**data, "updated": datetime.datetime.now().isoformat()}
    with open(DATA_DIR / "sessions.json", "w") as f: json.dump(sessions, f, indent=2)

def is_online():
    if not REQUESTS_OK: return False
    try: req_lib.get("https://8.8.8.8", timeout=3); return True
    except: return False

def extract_pdf_text(filepath):
    if not FITZ_OK: return "[PDF extraction unavailable]"
    try:
        doc = fitz.open(str(filepath))
        text = "".join(page.get_text() for page in doc)
        doc.close(); return text[:8000]
    except Exception as e: return f"[PDF error: {e}]"

DEFAULT_SYSTEM = (
    "You are OphthaCare AI, an ophthalmology health research assistant. Help patients understand "
    "eye conditions, medications, surgical procedures, and vision health from published ophthalmology "
    "literature. ALWAYS start with a brief AI research disclaimer. Reference AAO, RCOphth, WHO, "
    "NICE, AIOS guidelines. ALWAYS end reminding them to consult a qualified ophthalmologist. "
    "For eye emergencies (sudden vision loss, chemical injury, penetrating injury, acute angle "
    "closure, flashes/floaters with curtain) advise immediate eye casualty or call 112/999/911."
)

def call_ai(prompt, system_prompt=None, max_tokens=2500, provider=None, api_key=None):
    if not AI_PROVIDERS_OK: return None, "ai_providers_missing"
    provider = validate_provider(provider)
    effective_key = sanitise_api_key(api_key) or DEFAULT_PROVIDER_KEYS.get(provider, "") or (API_KEY if provider == "anthropic" else "")
    if not effective_key or not REQUESTS_OK or not is_online(): return None, "offline_or_no_key"
    text, mode = ai_providers.call_ai(provider, effective_key, prompt, system_prompt or DEFAULT_SYSTEM, max_tokens)
    if text is None: log.error(f"{provider} API error: {mode}"); return None, mode
    return text, "live_ai"

def build_offline_response(topic, patient_info=None):
    topic_l = topic.lower()
    kb_key = next((k for k in KNOWLEDGE if k.replace("_"," ") in topic_l or topic_l in k.replace("_"," ")), None)
    lines = ["# OphthaCare AI Research Report", f"**Topic:** {topic}",
             "**Mode:** Offline Research (Embedded Ophthalmology Knowledge Base)", "",
             "> DISCLAIMER: AI-generated educational information. NOT medical advice. "
             "ALWAYS consult a qualified ophthalmologist. EYE EMERGENCY: Call 112/999/911.", "", "---", ""]
    if kb_key:
        kb = KNOWLEDGE[kb_key]
        lines.append(f"## {kb.get('name', topic)}\n")
        for field, value in kb.items():
            if field == "name": continue
            if isinstance(value, str): lines += [f"**{field.replace('_',' ').title()}:** {value}", ""]
            elif isinstance(value, list): lines += [f"### {field.replace('_',' ').title()}"] + [f"- {i}" for i in value] + [""]
    else:
        lines += [f"## Research Overview: {topic}", "", f"Enable live AI in Settings for detailed research on {topic}.", ""]
    lines += ["---", "## India Eye Care Resources",
              "- AIOS: All India Ophthalmological Society (aios.org)",
              "- LV Prasad Eye Institute, Hyderabad: lvpei.org",
              "- Aravind Eye Hospital: aravind.org",
              "- Sankara Nethralaya, Chennai: sankaranethralaya.org",
              "- AIIMS RP Centre, New Delhi: aiims.edu", "- Emergency: 112", "", f"WARNING - {DISCLAIMER}"]
    return "\n".join(lines)

@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(STATIC_DIR), filename)

@app.route("/api/health")
def health():
    return jsonify({"status":"ok","version":VERSION,"online":is_online(),"pdf_extract":FITZ_OK,"timestamp":datetime.datetime.now().isoformat()})

@app.route("/api/upload", methods=["POST"])
def upload():
    if "files" not in request.files: return jsonify({"error":"No files"}), 400
    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id; session_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for f in request.files.getlist("files"):
        if not f.filename: continue
        ext = Path(f.filename).suffix.lower()
        safe = f"{uuid.uuid4().hex}{ext}"; dest = session_dir / safe; f.save(str(dest))
        extracted = extract_pdf_text(dest) if ext == ".pdf" else ""
        results.append({"original":f.filename,"saved":safe,"type":"pdf" if ext==".pdf" else ("image" if ext in [".jpg",".jpeg",".png"] else "text"),"size_kb":round(dest.stat().st_size/1024,1),"has_content":bool(extracted)})
    existing = load_sessions().get(session_id, {})
    save_session(session_id, {"session_id":session_id,"files":existing.get("files",[])+results})
    return jsonify({"success":True,"session_id":session_id,"uploaded":len(results),"files":results,"disclaimer":DISCLAIMER})

@app.route("/api/analyse", methods=["POST"])
def analyse():
    data = request.json or {}
    if not rate_limit_check(): return jsonify({"error":"Rate limit exceeded","mode":"rate_limited"}), 429
    topic = data.get("topic","General Ophthalmology"); condition = data.get("condition","")
    patient_info = data.get("patient_info",{}); provider = validate_provider(data.get("provider","anthropic"))
    effective_key = sanitise_api_key(data.get("api_key","")) or DEFAULT_PROVIDER_KEYS.get(provider,"") or (API_KEY if provider=="anthropic" else "")
    prompt = f"""Ophthalmology Research Request: {topic} / {condition}
Patient: Age {patient_info.get('age','not specified')}, Symptoms: {patient_info.get('symptoms','not specified')}
Medications: {patient_info.get('medications','none')}, Other conditions: {patient_info.get('conditions','none')}
Cover: overview, investigations (slit-lamp, OCT, visual fields, fundoscopy), treatment options (medical/laser/surgical), eye drop dosing from AAO/RCOphth/NICE, emergency red flags, India eye hospitals, questions for ophthalmologist, visual prognosis."""
    result, mode = call_ai(prompt, provider=provider, api_key=effective_key) if (effective_key and is_online()) else (None,"offline")
    if not result: result = build_offline_response(topic, patient_info); mode = "offline"
    return jsonify({"success":True,"mode":mode,"analysis":result,"topic":topic,"disclaimer":DISCLAIMER,"timestamp":datetime.datetime.now().isoformat()})

@app.route("/api/condition/<condition_name>")
def condition_detail(condition_name):
    cn = condition_name.lower().replace("-","_").replace(" ","_")
    if cn in KNOWLEDGE: return jsonify({"success":True,"mode":"offline_kb","condition":KNOWLEDGE[cn],"disclaimer":DISCLAIMER})
    provider = validate_provider(request.args.get("provider","anthropic"))
    effective_key = sanitise_api_key(request.args.get("api_key","")) or DEFAULT_PROVIDER_KEYS.get(provider,"") or (API_KEY if provider=="anthropic" else "")
    prompt = f"Comprehensive ophthalmology research on {condition_name}: definition, causes, symptoms, diagnosis (slit-lamp, OCT, fields, fundoscopy), treatment (drops/laser/surgery), prognosis. Reference AAO, RCOphth, WHO, NICE."
    result, mode = call_ai(prompt, provider=provider, api_key=effective_key)
    if not result: result = build_offline_response(condition_name); mode = "offline"
    return jsonify({"success":True,"mode":mode,"content":result,"disclaimer":DISCLAIMER})

@app.route("/api/vision/interpret", methods=["POST"])
def interpret_vision():
    data = request.json or {}
    test_type = data.get("test_type","Eye Examination"); findings = data.get("findings",""); context = data.get("context","")
    provider = validate_provider(data.get("provider","anthropic"))
    effective_key = sanitise_api_key(data.get("api_key","")) or DEFAULT_PROVIDER_KEYS.get(provider,"") or (API_KEY if provider=="anthropic" else "")
    prompt = f"Eye test interpretation research: {test_type}. Findings: {findings}. Context: {context}. Explain findings in plain English, clinical significance, typical follow-up, relevant grading systems, questions to ask the ophthalmologist. Research only - actual interpretation requires qualified eye care professional."
    result, mode = call_ai(prompt, provider=provider, api_key=effective_key)
    if not result: result = f"Eye test interpretation research for {test_type}. Enable live AI in Settings for detailed research. Consult your ophthalmologist for actual interpretation."; mode = "offline"
    return jsonify({"success":True,"mode":mode,"content":result,"disclaimer":DISCLAIMER})

@app.route("/api/chat/send", methods=["POST"])
def chat_send():
    data = request.json or {}
    message = data.get("message","").strip()
    if not message: return jsonify({"error":"Empty message"}), 400
    provider = validate_provider(data.get("provider","anthropic"))
    effective_key = sanitise_api_key(data.get("api_key","")) or DEFAULT_PROVIDER_KEYS.get(provider,"") or (API_KEY if provider=="anthropic" else "")
    result = None
    if data.get("request_ai") and is_online() and effective_key:
        result, _ = call_ai(f"Ophthalmology patient question: '{message}'. Respond in 3-4 paragraphs, compassionate and evidence-based. End with: consult ophthalmologist reminder and for eye emergencies (sudden vision loss, chemical injury, penetrating injury) attend eye casualty immediately or call 112/999/911.", max_tokens=800, provider=provider, api_key=effective_key)
    return jsonify({"success":True,"ai_response":result,"disclaimer":"Not medical advice. Consult your ophthalmologist."})

@app.route("/api/report/generate", methods=["POST"])
def generate_report():
    data = request.json or {}
    topic = data.get("topic","General Ophthalmology"); patient = data.get("patient_info",{})
    provider = validate_provider(data.get("provider","anthropic"))
    effective_key = sanitise_api_key(data.get("api_key","")) or DEFAULT_PROVIDER_KEYS.get(provider,"") or (API_KEY if provider=="anthropic" else "")
    content = build_offline_response(topic, patient)
    if effective_key and is_online():
        ai_content, _ = call_ai(f"Generate comprehensive ophthalmology research report for: {topic}. Patient: {patient}. Cover diagnosis, treatment options, eye drops, surgery, follow-up.", max_tokens=3500, provider=provider, api_key=effective_key)
        if ai_content: content = ai_content
    report_id = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    report = {"report_id":report_id,"generated":datetime.datetime.now().isoformat(),"topic":topic,"patient":patient,"content":content,"disclaimer":DISCLAIMER}
    with open(REPORTS_DIR / f"{report_id}.json","w",encoding="utf-8") as f: json.dump(report,f,indent=2,ensure_ascii=False)
    return jsonify(report)

@app.route("/api/providers")
def list_providers():
    if not AI_PROVIDERS_OK: return jsonify({"providers":[],"error":"ai_providers module not available"})
    return jsonify({"providers":[{"id":k,"label":v["label"],"default_model":v["default_model"],"key_prefix":v["key_prefix"],"get_key_url":v["get_key_url"],"server_default_configured":bool(DEFAULT_PROVIDER_KEYS.get(k))} for k,v in ai_providers.PROVIDERS.items()],"online":is_online()})

@app.route("/api/status")
def status():
    any_key = bool(API_KEY) or any(DEFAULT_PROVIDER_KEYS.values())
    return jsonify({"server":"running","version":VERSION,"online":is_online(),"mode":"live_ai" if (any_key and is_online()) else "offline_research","capabilities":{"pdf":FITZ_OK,"images":PIL_OK,"live_ai":bool(any_key and is_online()),"offline":True,"multi_provider":AI_PROVIDERS_OK,"rate_limiting":True,"aes256_frontend":True},"knowledge_base":list(KNOWLEDGE.keys()),"providers":list(ai_providers.PROVIDERS.keys()) if AI_PROVIDERS_OK else [],"disclaimer":DISCLAIMER})

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--port", type=int, default=PORT); args = parser.parse_args()
    save_knowledge()
    log.info("=" * 60); log.info(f"  OphthaCare AI Server v{VERSION} - Port {args.port}")
    log.info(f"  Online: {is_online()}"); log.info(f"  URL: http://localhost:{args.port}"); log.info("=" * 60)
    app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True, use_reloader=False)
