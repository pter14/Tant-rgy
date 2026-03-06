from flask import Flask, render_template, request, jsonify
import unicodedata
import json

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
    base = normalize(name)[:4]
    ids = [s["id"] for s in data_store["subjects"]]
    if base not in ids:
        return base
    i = 2
    while f"{base}{i}" in ids:
        i += 1
    return f"{base}{i}"

def generate_teacher_id(name):
    parts = name.strip().split()
    base = "".join(p[0].upper() for p in parts if p)
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

@app.route("/add_class", methods=["POST"])
def add_class():
    cid = request.form["class_id"]
    name = generate_class_name(cid)
    data_store["classes"].append({"id": cid, "name": name})
    return jsonify(data_store)

@app.route("/add_subject", methods=["POST"])
def add_subject():
    name = request.form["subject_name"]
    sid = generate_subject_id(name)

    per_class = {}
    for c in data_store["classes"]:
        hours = request.form.get(f"hours_{c['id']}", 0)
        per_class[c["id"]] = int(hours)

    data_store["subjects"].append({
        "id": sid,
        "name": name,
        "per_class_weekly_hours": per_class
    })

    return jsonify(data_store)

@app.route("/add_teacher", methods=["POST"])
def add_teacher():
    name = request.form["teacher_name"]
    tid = generate_teacher_id(name)

    teaches = request.form.getlist("subjects")
    fixed_classes = request.form.getlist("classes")

    data_store["teachers"].append({
        "id": tid,
        "name": name,
        "teaches_subjects": teaches,
        "fixed_classes": fixed_classes,
        "weekly_required_hours": int(request.form["weekly_hours"])
    })

    return jsonify(data_store)

@app.route("/export")
def export():
    return jsonify(data_store)

if __name__ == "__main__":
    app.run(debug=True)
