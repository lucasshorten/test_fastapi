"""
Gestion des annotations utilisateur.

Chaque annotateur écrit dans SON PROPRE fichier CSV (<data_dir>/annotations/annotations_<user>.csv).
=> aucune écriture concurrente sur un même fichier, donc pas besoin de verrou de fichier
   même si plusieurs personnes travaillent en même temps.

data_dir est toujours passé explicitement par l'appelant (le data/ de
l'instance en cours — voir DATA_DIR dans main.py) : ce module ne doit pas
supposer un dossier fixe, plusieurs instances tournant en parallèle avec
des data/ différents.

Pour une vue consolidée (export, relecture), `load_all_annotations()` concatène
tous les fichiers du dossier.
"""
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

COLUMNS = [
    "timestamp", "user", "patient_id", "sejour_key",
    "item_type",   # "suggestion" | "code_valide" | "manuel"
    "item_id",
    "action",      # "validé" | "rejeté" | "annulé" | "modifié" | "ajouté" | "supprimé" | "restauré"
    "code", "libelle", "type_code", "commentaire",
]


def _annotations_dir(data_dir: Path) -> Path:
    d = Path(data_dir) / "annotations"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_filename(user: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", user.strip()) or "anonyme"
    return f"annotations_{slug}.csv"


def user_file(data_dir: Path, user: str) -> Path:
    return _annotations_dir(data_dir) / _safe_filename(user)


def load_user_annotations(data_dir: Path, user: str) -> pd.DataFrame:
    path = user_file(data_dir, user)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    return pd.read_csv(path)


def append_annotation(data_dir: Path, user: str, patient_id: str, sejour_key: str, item_type: str,
                       item_id: str, action: str, code: str = "", libelle: str = "",
                       type_code: str = "", commentaire: str = "") -> None:
    row = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": user, "patient_id": patient_id, "sejour_key": sejour_key,
        "item_type": item_type, "item_id": item_id, "action": action,
        "code": code, "libelle": libelle, "type_code": type_code, "commentaire": commentaire,
    }
    path = user_file(data_dir, user)
    df_row = pd.DataFrame([row], columns=COLUMNS)
    df_row.to_csv(path, mode="a", header=not path.exists(), index=False)


def new_manual_id() -> str:
    return f"manuel-{uuid.uuid4().hex[:8]}"


def latest_actions(user_annotations: pd.DataFrame, patient_id: str, sejour_key: str) -> pd.DataFrame:
    """Renvoie, pour chaque item_id du séjour, sa dernière action connue pour cet utilisateur."""
    if user_annotations.empty:
        return user_annotations
    subset = user_annotations[
        (user_annotations["patient_id"] == patient_id) & (user_annotations["sejour_key"] == sejour_key)
    ].copy()
    if subset.empty:
        return subset
    subset["timestamp"] = pd.to_datetime(subset["timestamp"])
    subset = subset.sort_values("timestamp")
    return subset.groupby("item_id", as_index=False).last()


def load_all_annotations(data_dir: Path) -> pd.DataFrame:
    """Concatène les CSV de tous les annotateurs (pour export / relecture consolidée)."""
    frames = []
    for f in _annotations_dir(data_dir).glob("annotations_*.csv"):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            continue
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(frames, ignore_index=True)
