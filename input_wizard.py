#!/usr/bin/env python3
# input_wizard.py
# Konzolos adatbekérő az órarend-generátorhoz (A - tantárgy-központú)
import json
from pathlib import Path

def ask(prompt, default=None, cast=str):
    while True:
        raw = input(f"{prompt}" + (f" [{default}]" if default is not None else "") + ": ").strip()
        if raw == "" and default is not None:
            return default
        try:
            return cast(raw)
        except Exception as e:
            print("Hibás érték, próbáld újra.")

def ask_choices(prompt, choices, allow_multiple=False, allow_empty=False):
    # choices: list of (id, label)
    print(prompt)
    for i,(cid,label) in enumerate(choices, start=1):
        print(f"{i}. {label}")
    while True:
        raw = input("Válassz szám(oka)t vesszővel elválasztva (Enter = üres): ").strip()
        if raw == "":
            if allow_empty:
                return []
            else:
                print("Nem lehet üres, válassz legalább egyet.")
                continue
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        try:
            idxs = [int(p)-1 for p in parts]
            vals = [choices[i][0] for i in idxs]
            if not allow_multiple and len(vals)>1:
                print("Kérlek csak egyet válassz.")
                continue
            return vals
        except Exception:
            print("Érvénytelen választás, próbáld újra.")

def main():
    print("=== Órarend segédlet - adatbekérő (A: tantárgy-központú) ===\n")
    # CONFIG
    print("Alapbeállítások (Enter = elfogadott alapértelmezés)\n")
    first_period_start = ask("Első óra kezdete (HH:MM)", "08:00", str)
    period_length = ask("Óra hossza percben", 45, int)
    break_length = ask("Rövid szünet hossza percben", 15, int)
    max_periods = ask("Max órák száma naponta", 7, int)
    lunch_start = ask("Ebédszünet kezdete (HH:MM)", "12:00", str)
    lunch_len = ask("Ebédszünet hossza percben", 60, int)

    config = {
        "days": ["Hétfő","Kedd","Szerda","Csütörtök","Péntek"],
        "first_period_start": first_period_start,
        "period_length_min": period_length,
        "break_length_min": break_length,
        "lunch_break": {"start_time": lunch_start, "duration_min": lunch_len},
        "max_periods_per_day": max_periods
    }

    # Classes
    classes = []
    print("\n--- Osztályok felvétele ---")
    while True:
        cid = input("Add meg az osztály azonosítóját (pl. 8A) (Enter üres = kész): ").strip()
        if cid == "":
            break
        name = input("Megjelenítendő név (Enter = azonosító): ").strip() or cid
        classes.append({"id": cid, "name": name})
    if not classes:
        print("Legalább 1 osztály szükséges. Kilépek.")
        return

    # Subjects (A-modell)
    subjects = []
    print("\n--- Tantárgyak felvétele (A - tantárgy-központú) ---")
    while True:
        sid = input("Add meg a tantárgy azonosítóját (pl. matematika) (Enter üres = kész): ").strip()
        if sid == "":
            break
        sname = input("Tantárgy megnevezése (Enter = azonosító): ").strip() or sid
        per_class = {}
        print("Add meg osztályonként a heti óraszámot (0 = nincs):")
        for cl in classes:
            while True:
                v = input(f" {cl['id']} ({cl['name']}): ").strip()
                if v == "":
                    v = "0"
                try:
                    vi = int(v)
                    if vi < 0:
                        raise ValueError
                    per_class[cl['id']] = vi
                    break
                except:
                    print("Adj meg egy nemnegatív egész számot.")
        subjects.append({
            "id": sid,
            "name": sname,
            "per_class_weekly_hours": per_class,
            "allow_double_periods": False
        })

    # Teachers
    teachers = []
    print("\n--- Tanárok felvétele ---")
    # prepare choices for subjects and classes
    subj_choices = [(s["id"], s["name"]) for s in subjects]
    class_choices = [(c["id"], c["name"]) for c in classes]
    while True:
        tid = input("Tanár azonosító (pl. kovacs_anna) (Enter üres = kész): ").strip()
        if tid == "":
            break
        tname = input("Tanár teljes neve: ").strip() or tid
        weekly = ask("Heti kötelező óraszám (int)", 18, int)
        print("Válaszd ki a tantárgy(ak)at, amiket tanít (több válasz is lehetséges):")
        teaches = ask_choices("Tantárgyak:", subj_choices, allow_multiple=True, allow_empty=False)
        print("Válaszd ki azokat az osztályokat, ahol biztosan tanít (Enter = nincs rögzítve):")
        fixed = ask_choices("Fix osztályok:", class_choices, allow_multiple=True, allow_empty=True)
        teachers.append({
            "id": tid,
            "name": tname,
            "weekly_required_hours": weekly,
            "teaches_subjects": teaches,
            "fixed_classes": fixed
        })

    data = {"config": config, "classes": classes, "subjects": subjects, "teachers": teachers, "assignments": []}
    outpath = Path(input("\nMentési fájl neve (pl. data.json): ").strip() or "data.json")
    with outpath.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nAdatok elmentve: {outpath.resolve()}")

if __name__ == "__main__":
    main()
