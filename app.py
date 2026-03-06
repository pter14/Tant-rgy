from flask import Flask, render_template, request, jsonify
import unicodedata

app = Flask(__name__)

data_store = {
    "config": {},
    "classes": [],
    "subjects": [],
    "teachers": []
}

# ----------------------
# SEGÉDFÜGGVÉNYEK
# ----------------------

def normalize(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().replace(" ", "")

def generate_subject_id(name):
    base = normalize(name)[:4] or "s"
    ids = [s["id"] for s in data_store["subjects"]]
    if base not in ids:
        return base
    i = 2
    while f"{base}{i}" in ids:
        i += 1
    return f"{base}{i}"

def generate_teacher_id(name):
    parts = name.strip().split()
    if not parts:
        return ""
    base = "".join(p[0].upper() for p in parts if p)
    if not base:
        base = "T"
    ids = [t["id"] for t in data_store["teachers"]]
    if base not in ids:
        return base
    i = 2
    while f"{base}{i}" in ids:
        i += 1
    return f"{base}{i}"

def generate_class_name(cid):
    cid = cid.strip()
    number = "".join(filter(str.isdigit, cid))
    letter = "".join(filter(str.isalpha, cid)).lower()
    if number and letter:
        return f"{number}.{letter}"
    return cid

# ----------------------
# ROUTES
# ----------------------

@app.route("/")
def index():
    return render_template("index.html", data=data_store)

@app.route("/data", methods=["GET"])
def get_data():
    return jsonify({"success": True, "data": data_store})

@app.route("/add_class", methods=["POST"])
def add_class():
    cid = request.json.get("class_id", "").strip()
    if not cid:
        return jsonify({"success": False, "error": "Hiányzó osztályazonosító"}), 400
    # check duplicates
    if any(c["id"] == cid for c in data_store["classes"]):
        return jsonify({"success": False, "error": "Már létezik ilyen azonosítójú osztály"}), 400
    name = generate_class_name(cid)
    data_store["classes"].append({"id": cid, "name": name})
    return jsonify({"success": True, "data": data_store})

@app.route("/add_subject", methods=["POST"])
def add_subject():
    name = request.json.get("subject_name", "").strip()
    per_class = request.json.get("per_class_weekly_hours", {})
    if not name:
        return jsonify({"success": False, "error": "Hiányzó tantárgynév"}), 400
    # validate per_class keys exist as classes
    for k in per_class.keys():
        if not any(c["id"] == k for c in data_store["classes"]):
            return jsonify({"success": False, "error": f"Ismeretlen osztály az óraszámok között: {k}"}), 400
    sid = generate_subject_id(name)
    data_store["subjects"].append({
        "id": sid,
        "name": name,
        "per_class_weekly_hours": {k: int(v) for k, v in per_class.items()}
    })
    return jsonify({"success": True, "data": data_store})

@app.route("/add_teacher", methods=["POST"])
def add_teacher():
    name = request.json.get("teacher_name", "").strip()
    weekly_raw = request.json.get("weekly_hours", "")
    teaches = request.json.get("teaches", [])
    fixed_classes = request.json.get("fixed_classes", [])
    if not name:
        return jsonify({"success": False, "error": "Hiányzó tanár név"}), 400
    try:
        weekly = int(weekly_raw) if weekly_raw != "" else 0
        if weekly < 0:
            raise ValueError
    except Exception:
        return jsonify({"success": False, "error": "A heti óraszámnak nemnegatív egésznek kell lennie"}), 400
    # validate subjects and classes exist
    for s in teaches:
        if not any(sub["id"] == s for sub in data_store["subjects"]):
            return jsonify({"success": False, "error": f"Ismeretlen tantárgy: {s}"}), 400
    for c in fixed_classes:
        if not any(cl["id"] == c for cl in data_store["classes"]):
            return jsonify({"success": False, "error": f"Ismeretlen osztály: {c}"}), 400

    tid = generate_teacher_id(name)
    data_store["teachers"].append({
        "id": tid,
        "name": name,
        "teaches_subjects": teaches,
        "fixed_classes": fixed_classes,
        "weekly_required_hours": weekly
    })
    return jsonify({"success": True, "data": data_store})

@app.route("/export", methods=["GET"])
def export():
    return jsonify(data_store)

if __name__ == "__main__":
    app.run(debug=True)
