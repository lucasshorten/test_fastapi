"""
Backend FastAPI :
- sert le frontend statique (static/index.html — le prototype quasi inchangé)
- expose les données de référence (Excel) en JSON, fusionnées avec les
  annotations de l'utilisateur courant
- reçoit les annotations et les ajoute au CSV propre à cet utilisateur

Lancer avec :  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import annotations_store as store

DATA_DIR = Path(__file__).parent / "data"
STATIC_DIR = Path(__file__).parent / "static"

TABLE_NAMES = ["patients", "sejours", "parcours", "documents", "fiches", "observations",
               "constantes", "biologie", "medicaments", "administrations",
               "codes_valides", "suggestions"]
TABLES = {n: pd.read_excel(DATA_DIR / f"{n}.xlsx") for n in TABLE_NAMES}

app = FastAPI(title="Dossier patient — API")


def table_for(name, patient_id, sejour_key=None):
    df = TABLES[name]
    df = df[df["patient_id"] == patient_id]
    if sejour_key is not None:
        df = df[df["sejour_key"] == sejour_key]
    return df


def _none_if_nan(v):
    return None if pd.isna(v) else v


def build_dossier(patient_id: str, user: str) -> dict:
    identity_row = TABLES["patients"][TABLES["patients"]["patient_id"] == patient_id].iloc[0]
    sejours_df = table_for("sejours", patient_id).sort_values("ordre")
    sejour_order = sejours_df["sejour_key"].tolist()

    user_annot = store.load_user_annotations(user)

    sejours = {}
    for _, s in sejours_df.iterrows():
        sk = s["sejour_key"]
        latest = store.latest_actions(user_annot, patient_id, sk)

        def latest_for(item_id):
            if latest.empty:
                return None
            rows = latest[latest["item_id"] == item_id]
            return rows.iloc[0] if not rows.empty else None

        parcours = [
            {"id": r["event_id"], "date": r["date"], "heure": r["heure"], "type": r["type"],
             "titre": r["titre"], "detail": r["detail"], "lieu": r["lieu"], "acteur": r["acteur"]}
            for _, r in table_for("parcours", patient_id, sk).iterrows()
        ]
        documents = [
            {"id": r["doc_id"], "date": r["date"], "type": r["type"], "titre": r["titre"],
             "auteur": r["auteur"], "uf": r["uf"], "excerpt": r["excerpt"], "fullText": r["full_text"],
             "highlight": r["highlight"]}
            for _, r in table_for("documents", patient_id, sk).iterrows()
        ]
        fiches = []
        fiches_df = table_for("fiches", patient_id, sk)
        for fid in fiches_df["fiche_id"].drop_duplicates():
            frows = fiches_df[fiches_df["fiche_id"] == fid].sort_values("champ_ordre")
            first = frows.iloc[0]
            fiches.append({
                "id": fid, "titre": first["titre"], "type": first["type"],
                "date": first["date"], "auteur": first["auteur"], "uf": first["uf"],
                "highlight": _none_if_nan(first["highlight"]) or "",
                "champs": [{"label": r["champ_label"], "valeur": r["champ_valeur"]}
                           for _, r in frows.iterrows()],
            })
        observations = [
            {"id": r["observation_id"], "date": r["date"], "auteur": r["auteur"], "uf": r["uf"],
             "categorie": r["categorie"], "highlight": _none_if_nan(r["highlight"]) or "",
             "texte": r["texte"]}
            for _, r in table_for("observations", patient_id, sk).iterrows()
        ]
        constantes = [
            {"date": r["date"], "fc": int(r["fc"]), "ta": r["ta"], "spo2": r["spo2"],
             "temp": r["temp"], "poids": r["poids"]}
            for _, r in table_for("constantes", patient_id, sk).iterrows()
        ]
        biologie = [
            {"date": r["date"], "ntprobnp": r["ntprobnp"], "creat": r["creat"], "dfg": r["dfg"],
             "crp": r["crp"], "k": r["k"], "hb": r["hb"], "leuco": r["leuco"], "na": r["na"],
             "glycemie": r["glycemie"]}
            for _, r in table_for("biologie", patient_id, sk).iterrows()
        ]
        medicaments = [
            {"id": r["med_id"], "nom": r["nom"], "dose": r["dose"], "voie": r["voie"],
             "frequence": r["frequence"], "indication": r["indication"],
             "prescripteur": r["prescripteur"], "debut": r["debut"],
             "fin": _none_if_nan(r["fin"]), "statut": r["statut"]}
            for _, r in table_for("medicaments", patient_id, sk).iterrows()
        ]
        administrations = [
            {"medId": r["med_id"], "date": r["date"], "heure": r["heure"]}
            for _, r in table_for("administrations", patient_id, sk).iterrows()
        ]

        codes_valides = []
        for _, r in table_for("codes_valides", patient_id, sk).iterrows():
            la = latest_for(r["code_id"])
            code, libelle, removed = r["code"], r["libelle"], bool(r["removed"])
            if la is not None:
                if la["action"] == "supprimé":
                    removed = True
                elif la["action"] == "restauré":
                    removed = False
                elif la["action"] == "modifié":
                    code, libelle = la["code"], la["libelle"]
            codes_valides.append({"id": r["code_id"], "code": code, "type": r["type"],
                                   "libelle": libelle, "notePar": r["note_par"],
                                   "date": r["date"], "removed": removed})
        if not latest.empty:
            manuels = latest[(latest["item_type"] == "manuel") & (latest["action"] != "supprimé")]
            for _, m in manuels.iterrows():
                codes_valides.append({"id": m["item_id"], "code": m["code"], "type": m["type_code"],
                                       "libelle": m["libelle"], "notePar": "Vous",
                                       "date": str(m["timestamp"])[:10], "removed": False,
                                       "manuel": True})

        suggestions = []
        for _, r in table_for("suggestions", patient_id, sk).iterrows():
            la = latest_for(r["suggestion_id"])
            status = la["action"] if la is not None else "pending"
            code, libelle, amended = r["code"], r["libelle"], False
            if la is not None and la["action"] == "modifié":
                code, libelle, amended = la["code"], la["libelle"], True
            if status == "annulé":
                status = "pending"
            suggestions.append({"id": r["suggestion_id"], "code": code, "type": r["type"],
                                 "libelle": libelle, "confiance": int(r["confiance"]),
                                 "source": {"kind": r["source_kind"], "id": r["source_id"]},
                                 "justification": r["justification"], "status": status,
                                 "amended": amended})

        sejours[sk] = {
            "idSejour": s["id_sejour"], "service": s["service"], "entree": s["entree"],
            "sortie": s["sortie"], "motif": s["motif"], "praticien": s["praticien"],
            "parcours": parcours, "documents": documents, "fiches": fiches, "observations": observations,
            "constantes": constantes,
            "biologie": biologie, "medicaments": medicaments, "administrations": administrations,
            "codesValides": codes_valides, "suggestions": suggestions,
        }

    return {
        "identity": {"id": patient_id, "sexe": identity_row["sexe"], "age": int(identity_row["age"])},
        "sejourOrder": sejour_order,
        "sejours": sejours,
    }


class AnnotationIn(BaseModel):
    user: str
    patient_id: str
    sejour_key: str
    item_type: str
    item_id: str
    action: str
    code: str = ""
    libelle: str = ""
    type_code: str = ""
    commentaire: str = ""


@app.get("/api/patients")
def list_patients():
    return TABLES["patients"]["patient_id"].tolist()


@app.get("/api/dossier/{patient_id}")
def get_dossier(patient_id: str, user: str = Query(...)):
    return build_dossier(patient_id, user)


@app.post("/api/annotate")
def post_annotate(a: AnnotationIn):
    store.append_annotation(a.user, a.patient_id, a.sejour_key, a.item_type, a.item_id,
                             a.action, a.code, a.libelle, a.type_code, a.commentaire)
    return {"ok": True}


@app.get("/api/export")
def export_all():
    df = store.load_all_annotations()
    return PlainTextResponse(df.to_csv(index=False), media_type="text/csv")


# Doit être monté en dernier : les routes /api/* déclarées ci-dessus sont
# résolues avant ce catch-all qui sert le frontend statique.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
