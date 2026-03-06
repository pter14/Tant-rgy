from flask import Flask, render_template, request, jsonify, send_file
import unicodedata
import json
from pathlib import Path

app = Flask(__name__)

DATA_FILE = Path(__file__).parent / "data.json"

# Alap adat
data_store = {
    "config": {},
    "classes": [],
    "subjects": [],
    "teachers": [],
    "years": [],
    "language_groups": [],
    "group_splits": []
}

# ----------------------
# Adat mentés / betöltés
# ----------------------
def load_data():
    global data_store
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data_store = json.load(f)
            print(f"Adatok betöltve: {DATA_FILE}")
        except Exception as e:
            print("Hiba a data.json betöltésekor:", e)
    else:
        print("Nincs data.json, üres kezdőállapot.")

def save_data():
    try:
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(data_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Hiba a data.json mentésekor:", e)

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

# ----- Add -----
@app.route("/add_class", methods=["POST"])
def add_class():
    cid = request.json.get("class_id", "").strip()
    if not cid:
        return jsonify({"success": False, "error": "Hiányzó osztályazonosító"}), 400
    if any(c["id"] == cid for c in data_store["classes"]):
        return jsonify({"success": False, "error": "Már létezik ilyen azonosítójú osztály"}), 400
    name = generate_class_name(cid)
    data_store["classes"].append({"id": cid, "name": name, "religion_choice": None})
    save_data()
    return jsonify({"success": True, "data": data_store})

@app.route("/add_subject", methods=["POST"])
def add_subject():
    name = request.json.get("subject_name", "").strip()
    per_class = request.json.get("per_class_weekly_hours", {})
    if not name:
        return jsonify({"success": False, "error": "Hiányzó tantárgynév"}), 400
    for k in per_class.keys():
        if not any(c["id"] == k for c in data_store["classes"]):
            return jsonify({"success": False, "error": f"Ismeretlen osztály az óraszámok között: {k}"}), 400
    sid = generate_subject_id(name)
    data_store["subjects"].append({
        "id": sid,
        "name": name,
        "per_class_weekly_hours": {k: int(v) for k, v in per_class.items()},
        "is_external": False,
        "mutually_exclusive_with": []
    })
    save_data()
    return jsonify({"success": True, "data": data_store})

# ----- Teacher add/update now supports fixed_assignments -----
@app.route("/add_teacher", methods=["POST"])
def add_teacher():
    name = request.json.get("teacher_name", "").strip()
    weekly_raw = request.json.get("weekly_hours", "")
    teaches = request.json.get("teaches", [])
    fixed_assignments = request.json.get("fixed_assignments", [])  # list of {"subject":..., "class":...}
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
    for fa in fixed_assignments:
        subj = fa.get("subject")
        cl = fa.get("class")
        if not any(sub["id"] == subj for sub in data_store["subjects"]):
            return jsonify({"success": False, "error": f"Ismeretlen tantárgy a fix beosztásban: {subj}"}), 400
        if not any(c["id"] == cl for c in data_store["classes"]):
            return jsonify({"success": False, "error": f"Ismeretlen osztály a fix beosztásban: {cl}"}), 400
        # ensure teacher actually teaches that subject
        if subj not in teaches:
            return jsonify({"success": False, "error": f"Fix beosztás megadva egy olyan tantárgyhoz, amit a tanár nem tanít: {subj}"}), 400

    tid = generate_teacher_id(name)
    data_store["teachers"].append({
        "id": tid,
        "name": name,
        "teaches_subjects": teaches,
        "fixed_assignments": fixed_assignments,
        "weekly_required_hours": weekly
    })
    save_data()
    return jsonify({"success": True, "data": data_store})

@app.route("/update_teacher", methods=["POST"])
def update_teacher():
    tid = request.json.get("id", "").strip()
    new_name = request.json.get("new_name", "").strip()
    weekly_raw = request.json.get("weekly_hours", "")
    teaches = request.json.get("teaches", None)
    fixed_assignments = request.json.get("fixed_assignments", None)
    if not tid:
        return jsonify({"success": False, "error": "Hiányzó tanár azonosító"}), 400
    for t in data_store["teachers"]:
        if t["id"] == tid:
            if new_name:
                t["name"] = new_name
            if weekly_raw != "":
                try:
                    weekly = int(weekly_raw)
                    if weekly < 0:
                        raise ValueError
                    t["weekly_required_hours"] = weekly
                except Exception:
                    return jsonify({"success": False, "error": "Heti óraszám nemnegatív egész legyen"}), 400
            if teaches is not None:
                for s in teaches:
                    if not any(sub["id"] == s for sub in data_store["subjects"]):
                        return jsonify({"success": False, "error": f"Ismeretlen tantárgy: {s}"}), 400
                t["teaches_subjects"] = teaches
                # remove any fixed_assignments for subjects no longer taught
                if "fixed_assignments" in t and t["fixed_assignments"]:
                    t["fixed_assignments"] = [fa for fa in t.get("fixed_assignments", []) if fa["subject"] in teaches]
            if fixed_assignments is not None:
                for fa in fixed_assignments:
                    subj = fa.get("subject")
                    cl = fa.get("class")
                    if not any(sub["id"] == subj for sub in data_store["subjects"]):
                        return jsonify({"success": False, "error": f"Ismeretlen tantárgy a fix beosztásban: {subj}"}), 400
                    if not any(c["id"] == cl for c in data_store["classes"]):
                        return jsonify({"success": False, "error": f"Ismeretlen osztály a fix beosztásban: {cl}"}), 400
                    # ensure teacher actually teaches that subject (if teaches was provided earlier, we trust it; otherwise check existing)
                    current_teaches = t.get("teaches_subjects", [])
                    if subj not in current_teaches:
                        return jsonify({"success": False, "error": f"Fix beosztás megadva egy olyan tantárgyhoz, amit a tanár nem tanít: {subj}"}), 400
                t["fixed_assignments"] = fixed_assignments
            save_data()
            return jsonify({"success": True, "data": data_store})
    return jsonify({"success": False, "error": "Nem található ilyen tanár"}), 404

# ----- Update / Delete for classes/subjects kept as before (not repeated here) -----
# For brevity, the rest of the update/delete endpoints remain the same as previous implementation.
# If you need them pasted in full, I can include them; assume they are unchanged and still present.

@app.route("/export", methods=["GET"])
def export():
    return jsonify(data_store)

@app.route("/download", methods=["GET"])
def download_file():
    if DATA_FILE.exists():
        return send_file(str(DATA_FILE), as_attachment=True, download_name="data.json")
    return jsonify({"success": False, "error": "Nincs mentett data.json fájl."}), 404

# Induláskor betöltjük az adatokat
if __name__ == "__main__":
    load_data()
    app.run(debug=True)
