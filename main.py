"""
Backend FastAPI :
- authentifie chaque relecteur (compte + mot de passe géré par l'admin,
  voir auth_store.py) et ne lui expose que les patients qui lui sont
  affectés
- sert le frontend statique (static/ — le prototype quasi inchangé)
- expose les données de référence (Excel) en JSON, fusionnées avec les
  annotations de l'utilisateur courant
- reçoit les annotations et les ajoute au CSV propre à cet utilisateur

Une instance = un dossier (contenant data/ et .auth/) = un port. Plusieurs
instances peuvent tourner en parallèle sur la même machine (voir
new_instance.py et launch_all.ps1) ; chacune a ses propres comptes et ses
propres données, totalement indépendants des autres.

Dossier d'instance choisi via la variable d'environnement
DOSSIER_INSTANCE_DIR (par défaut : le dossier de ce fichier).

Lancer avec :  uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
import os
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import annotations_store as store
import auth_store
import rules_store

INSTANCE_DIR = Path(os.environ.get("DOSSIER_INSTANCE_DIR", Path(__file__).parent))
DATA_DIR = INSTANCE_DIR / "data"
STATIC_DIR = Path(__file__).parent / "static"
SESSION_COOKIE = "session"

TABLE_NAMES = ["patients", "sejours", "parcours", "documents", "fiches", "observations",
               "constantes", "biologie", "medicaments", "administrations",
               "codes_valides", "suggestions"]
TABLES = {n: pd.read_excel(DATA_DIR / f"{n}.xlsx") for n in TABLE_NAMES}
ALL_PATIENT_IDS = TABLES["patients"]["patient_id"].tolist()

auth_store.init_db(INSTANCE_DIR)
if auth_store.user_count(INSTANCE_DIR) == 0:
    print(f"\nAucun compte configuré pour cette instance ({INSTANCE_DIR}).")
    print("Créez le premier compte admin avec :")
    print(f'    python auth_store.py "{INSTANCE_DIR}" create-user <votre_nom> --role admin\n')

app = FastAPI(title="Dossier patient — API")


# ------------------------------------------------------------- authentification --

def current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    username = auth_store.verify_session_token(INSTANCE_DIR, token) if token else None
    user = auth_store.get_user(INSTANCE_DIR, username) if username else None
    if user is None:
        raise HTTPException(status_code=401, detail="Non authentifié")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Réservé aux administrateurs")
    return user


def visible_patient_ids(user: dict) -> set:
    if user["role"] == "admin":
        return set(ALL_PATIENT_IDS)
    return set(auth_store.get_assigned_patients(INSTANCE_DIR, user["username"]))


class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(body: LoginIn):
    user = auth_store.authenticate(INSTANCE_DIR, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Identifiant ou mot de passe incorrect")
    token = auth_store.make_session_token(INSTANCE_DIR, user["username"])
    response = JSONResponse(user)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax",
                         max_age=auth_store.SESSION_TTL_SECONDS, path="/")
    return response


@app.post("/api/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/api/me")
def me(user: dict = Depends(current_user)):
    return user


# ------------------------------------------------------------------- dossier --

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

    user_annot = store.load_user_annotations(DATA_DIR, user)

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
                                 "amended": amended, "regleId": _none_if_nan(r["regle_id"])})

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
def list_patients(user: dict = Depends(current_user)):
    allowed = visible_patient_ids(user)
    return [pid for pid in ALL_PATIENT_IDS if pid in allowed]


@app.get("/api/dossier/{patient_id}")
def get_dossier(patient_id: str, user: dict = Depends(current_user)):
    if patient_id not in visible_patient_ids(user):
        raise HTTPException(status_code=403, detail="Patient non accessible pour ce compte")
    return build_dossier(patient_id, user["username"])


@app.post("/api/annotate")
def post_annotate(a: AnnotationIn, user: dict = Depends(current_user)):
    if a.patient_id not in visible_patient_ids(user):
        raise HTTPException(status_code=403, detail="Patient non accessible pour ce compte")
    store.append_annotation(DATA_DIR, user["username"], a.patient_id, a.sejour_key, a.item_type,
                             a.item_id, a.action, a.code, a.libelle, a.type_code, a.commentaire)
    return {"ok": True}


@app.get("/api/export")
def export_all(admin: dict = Depends(require_admin)):
    df = store.load_all_annotations(DATA_DIR)
    return PlainTextResponse(df.to_csv(index=False), media_type="text/csv")


# --------------------------------------------------------------- règles IA --
# Dictionnaire des règles/algorithmes de détection : partagé entre tous les
# comptes de l'instance (pas seulement les admins), purement documentaire —
# le modifier n'affecte jamais les suggestions déjà générées.

class RuleUpdateIn(BaseModel):
    titre: str | None = None
    logique: str | None = None
    description: str | None = None


class RuleCommentIn(BaseModel):
    texte: str


@app.get("/api/rules")
def list_rules(user: dict = Depends(current_user)):
    return rules_store.load_rules(DATA_DIR)


@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: str, body: RuleUpdateIn, user: dict = Depends(current_user)):
    try:
        return rules_store.update_rule(DATA_DIR, rule_id, titre=body.titre, logique=body.logique,
                                        description=body.description)
    except KeyError:
        raise HTTPException(status_code=404, detail="Règle introuvable")


@app.post("/api/rules/{rule_id}/comments")
def add_rule_comment(rule_id: str, body: RuleCommentIn, user: dict = Depends(current_user)):
    texte = body.texte.strip()
    if not texte:
        raise HTTPException(status_code=400, detail="Commentaire vide")
    try:
        return rules_store.add_comment(DATA_DIR, rule_id, user["username"], texte)
    except KeyError:
        raise HTTPException(status_code=404, detail="Règle introuvable")


# --------------------------------------------------------------------- admin --

class NewUserIn(BaseModel):
    username: str
    password: str
    role: str = "user"
    patient_ids: list[str] = []


class UpdateUserIn(BaseModel):
    password: str | None = None
    role: str | None = None
    patient_ids: list[str] | None = None


def _admin_usernames() -> list[str]:
    return [u["username"] for u in auth_store.list_users(INSTANCE_DIR) if u["role"] == "admin"]


@app.get("/api/admin/users")
def admin_list_users(admin: dict = Depends(require_admin)):
    return auth_store.list_users(INSTANCE_DIR)


@app.get("/api/admin/patients")
def admin_list_patients(admin: dict = Depends(require_admin)):
    return [
        {"id": r["patient_id"], "sexe": r["sexe"], "age": int(r["age"])}
        for _, r in TABLES["patients"].iterrows()
    ]


@app.post("/api/admin/users")
def admin_create_user(body: NewUserIn, admin: dict = Depends(require_admin)):
    try:
        auth_store.create_user(INSTANCE_DIR, body.username, body.password,
                                role=body.role, patient_ids=body.patient_ids)
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.put("/api/admin/users/{username}")
def admin_update_user(username: str, body: UpdateUserIn, admin: dict = Depends(require_admin)):
    try:
        if body.role is not None and body.role != "admin":
            if username in _admin_usernames() and _admin_usernames() == [username]:
                raise HTTPException(status_code=400,
                                     detail="Impossible de retirer le dernier compte administrateur")
        if body.password is not None:
            auth_store.set_password(INSTANCE_DIR, username, body.password)
        if body.role is not None:
            auth_store.set_role(INSTANCE_DIR, username, body.role)
        if body.patient_ids is not None:
            auth_store.set_assigned_patients(INSTANCE_DIR, username, body.patient_ids)
    except KeyError:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.delete("/api/admin/users/{username}")
def admin_delete_user(username: str, admin: dict = Depends(require_admin)):
    if username in _admin_usernames() and _admin_usernames() == [username]:
        raise HTTPException(status_code=400,
                             detail="Impossible de supprimer le dernier compte administrateur")
    try:
        auth_store.delete_user(INSTANCE_DIR, username)
    except KeyError:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    return {"ok": True}


# Doit être monté en dernier : les routes /api/* déclarées ci-dessus sont
# résolues avant ce catch-all qui sert le frontend statique.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
