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
    "teachers": []
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
    data_store["classes"].append({"id": cid, "name": name})
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
        "per_class_weekly_hours": {k: int(v) for k, v in per_class.items()}
    })
    save_data()
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
    save_data()
    return jsonify({"success": True, "data": data_store})

# ----- Update -----
@app.route("/update_class", methods=["POST"])
def update_class():
    cid = request.json.get("id", "").strip()
    new_name = request.json.get("new_name", "").strip()
    if not cid:
        return jsonify({"success": False, "error": "Hiányzó osztály azonosító"}), 400
    for c in data_store["classes"]:
        if c["id"] == cid:
            if new_name:
                c["name"] = new_name
                save_data()
                return jsonify({"success": True, "data": data_store})
            else:
                return jsonify({"success": False, "error": "Üres új név"}), 400
    return jsonify({"success": False, "error": "Nem található ilyen osztály"}), 404

@app.route("/update_subject", methods=["POST"])
def update_subject():
    sid = request.json.get("id", "").strip()
    new_name = request.json.get("new_name", "").strip()
    per_class = request.json.get("per_class_weekly_hours", {})
    if not sid:
        return jsonify({"success": False, "error": "Hiányzó tantárgy azonosító"}), 400
    for s in data_store["subjects"]:
        if s["id"] == sid:
            if new_name:
                s["name"] = new_name
            if per_class:
                # validate keys
                for k in per_class.keys():
                    if not any(c["id"] == k for c in data_store["classes"]):
                        return jsonify({"success": False, "error": f"Ismeretlen osztály: {k}"}), 400
                s["per_class_weekly_hours"] = {k: int(v) for k, v in per_class.items()}
            save_data()
            return jsonify({"success": True, "data": data_store})
    return jsonify({"success": False, "error": "Nem található ilyen tantárgy"}), 404

@app.route("/update_teacher", methods=["POST"])
def update_teacher():
    tid = request.json.get("id", "").strip()
    new_name = request.json.get("new_name", "").strip()
    weekly_raw = request.json.get("weekly_hours", "")
    teaches = request.json.get("teaches", None)
    fixed_classes = request.json.get("fixed_classes", None)
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
            if fixed_classes is not None:
                for c in fixed_classes:
                    if not any(cl["id"] == c for cl in data_store["classes"]):
                        return jsonify({"success": False, "error": f"Ismeretlen osztály: {c}"}), 400
                t["fixed_classes"] = fixed_classes
            save_data()
            return jsonify({"success": True, "data": data_store})
    return jsonify({"success": False, "error": "Nem található ilyen tanár"}), 404

# ----- Delete -----
@app.route("/delete_class", methods=["POST"])
def delete_class():
    cid = request.json.get("id", "").strip()
    if not cid:
        return jsonify({"success": False, "error": "Hiányzó osztály azonosító"}), 400
    # remove class
    data_store["classes"] = [c for c in data_store["classes"] if c["id"] != cid]
    # remove from subjects per_class_weekly_hours
    for s in data_store["subjects"]:
        if cid in s.get("per_class_weekly_hours", {}):
            s["per_class_weekly_hours"].pop(cid, None)
    # remove from teachers fixed_classes
    for t in data_store["teachers"]:
        if cid in t.get("fixed_classes", []):
            t["fixed_classes"] = [x for x in t["fixed_classes"] if x != cid]
    save_data()
    return jsonify({"success": True, "data": data_store})

@app.route("/delete_subject", methods=["POST"])
def delete_subject():
    sid = request.json.get("id", "").strip()
    if not sid:
        return jsonify({"success": False, "error": "Hiányzó tantárgy azonosító"}), 400
    data_store["subjects"] = [s for s in data_store["subjects"] if s["id"] != sid]
    # remove from teachers
    for t in data_store["teachers"]:
        if sid in t.get("teaches_subjects", []):
            t["teaches_subjects"] = [x for x in t["teaches_subjects"] if x != sid]
    save_data()
    return jsonify({"success": True, "data": data_store})

@app.route("/delete_teacher", methods=["POST"])
def delete_teacher():
    tid = request.json.get("id", "").strip()
    if not tid:
        return jsonify({"success": False, "error": "Hiányzó tanár azonosító"}), 400
    data_store["teachers"] = [t for t in data_store["teachers"] if t["id"] != tid]
    save_data()
    return jsonify({"success": True, "data": data_store})

# export / download
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
