"""
Comptes (authentification) et affectations patient <-> utilisateur.

Un fichier YAML par instance déployée : <instance_dir>/.auth/credentials.yaml,
sur le modèle de .streamlit/ — un dossier de config à côté du code et de
data/, pas une base de données. Chaque instance (= un dossier = un port,
voir new_instance.py / instances.json) a donc sa propre liste de comptes,
indépendante des autres instances, et le fichier reste ouvrable/corrigeable
à la main si besoin.

Mots de passe : jamais stockés en clair, hachés avec PBKDF2-HMAC-SHA256
(hashlib, aucune dépendance supplémentaire pour le hachage).

Sessions : jeton signé par HMAC porté dans un cookie, pas de table de
sessions à nettoyer — la clé de signature vit dans le même fichier YAML.
"""
import argparse
import getpass
import hashlib
import hmac
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ITERATIONS = 200_000
SESSION_TTL_SECONDS = 60 * 60 * 12  # 12h
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def _credentials_path(instance_dir: Path) -> Path:
    return Path(instance_dir) / ".auth" / "credentials.yaml"


def _load(instance_dir: Path) -> dict:
    """Lit le fichier de credentials, en le créant (avec une clé de session
    fraîche) au tout premier appel — pour que cette clé soit stable d'un
    appel à l'autre plutôt que régénérée tant qu'aucun compte n'existe."""
    path = _credentials_path(instance_dir)
    if not path.exists():
        doc = {"users": {}, "secret_key": secrets.token_hex(32)}
        _save(instance_dir, doc)
        return doc
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    changed = False
    if "users" not in doc:
        doc["users"] = {}
        changed = True
    if "secret_key" not in doc:
        doc["secret_key"] = secrets.token_hex(32)
        changed = True
    if changed:
        _save(instance_dir, doc)
    return doc


def _save(instance_dir: Path, doc: dict) -> None:
    path = _credentials_path(instance_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)


def init_db(instance_dir: Path) -> None:
    """Crée le fichier de credentials s'il n'existe pas encore."""
    if not _credentials_path(instance_dir).exists():
        _save(instance_dir, _load(instance_dir))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    _, digest_hex = _hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(digest_hex, hash_hex)


def _check_username(username: str) -> None:
    if not USERNAME_RE.match(username or ""):
        raise ValueError("Identifiant invalide (lettres, chiffres, '_', '.', '-' uniquement)")


def _check_password(password: str) -> None:
    if not password or len(password) < 8:
        raise ValueError("Mot de passe trop court (8 caractères minimum)")


# --------------------------------------------------------------- comptes ---

def user_count(instance_dir: Path) -> int:
    return len(_load(instance_dir)["users"])


def create_user(instance_dir: Path, username: str, password: str, role: str = "user",
                 patient_ids: list[str] | None = None) -> None:
    _check_username(username)
    if role not in ("admin", "user"):
        raise ValueError("role doit être 'admin' ou 'user'")
    _check_password(password)
    doc = _load(instance_dir)
    if username in doc["users"]:
        raise ValueError(f"Le compte « {username} » existe déjà")
    salt_hex, hash_hex = _hash_password(password)
    doc["users"][username] = {
        "role": role, "salt": salt_hex, "password_hash": hash_hex,
        "created_at": _now(), "patients": list(patient_ids or []),
    }
    _save(instance_dir, doc)


def authenticate(instance_dir: Path, username: str, password: str) -> dict | None:
    user = _load(instance_dir)["users"].get(username)
    if user is None or not _verify_password(password, user["salt"], user["password_hash"]):
        return None
    return {"username": username, "role": user["role"]}


def get_user(instance_dir: Path, username: str) -> dict | None:
    user = _load(instance_dir)["users"].get(username)
    return {"username": username, "role": user["role"]} if user else None


def list_users(instance_dir: Path) -> list[dict]:
    users = _load(instance_dir)["users"]
    return [
        {"username": name, "role": u["role"], "patientCount": len(u.get("patients", [])),
         "patients": list(u.get("patients", []))}
        for name, u in sorted(users.items())
    ]


def set_password(instance_dir: Path, username: str, new_password: str) -> None:
    _check_password(new_password)
    doc = _load(instance_dir)
    if username not in doc["users"]:
        raise KeyError(username)
    salt_hex, hash_hex = _hash_password(new_password)
    doc["users"][username]["salt"] = salt_hex
    doc["users"][username]["password_hash"] = hash_hex
    _save(instance_dir, doc)


def set_role(instance_dir: Path, username: str, role: str) -> None:
    if role not in ("admin", "user"):
        raise ValueError("role doit être 'admin' ou 'user'")
    doc = _load(instance_dir)
    if username not in doc["users"]:
        raise KeyError(username)
    doc["users"][username]["role"] = role
    _save(instance_dir, doc)


def delete_user(instance_dir: Path, username: str) -> None:
    doc = _load(instance_dir)
    if username not in doc["users"]:
        raise KeyError(username)
    del doc["users"][username]
    _save(instance_dir, doc)


# ----------------------------------------------------------- affectations --

def get_assigned_patients(instance_dir: Path, username: str) -> list[str]:
    user = _load(instance_dir)["users"].get(username)
    return list(user.get("patients", [])) if user else []


def set_assigned_patients(instance_dir: Path, username: str, patient_ids: list[str]) -> None:
    doc = _load(instance_dir)
    if username not in doc["users"]:
        raise KeyError(username)
    doc["users"][username]["patients"] = list(dict.fromkeys(patient_ids))  # dédoublonne, garde l'ordre
    _save(instance_dir, doc)


# --------------------------------------------------------------- sessions --

def make_session_token(instance_dir: Path, username: str) -> str:
    secret_key = _load(instance_dir)["secret_key"]
    expiry = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{username}.{expiry}"
    sig = hmac.new(bytes.fromhex(secret_key), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_session_token(instance_dir: Path, token: str) -> str | None:
    try:
        username, expiry_str, sig = token.rsplit(".", 2)
        expiry = int(expiry_str)
    except (ValueError, AttributeError):
        return None
    secret_key = _load(instance_dir)["secret_key"]
    expected = hmac.new(bytes.fromhex(secret_key), f"{username}.{expiry_str}".encode("utf-8"),
                         hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    if time.time() > expiry:
        return None
    return username


# --------------------------------------------------------------------- CLI --

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Gestion des comptes d'une instance (.auth/credentials.yaml).")
    parser.add_argument("instance_dir", type=Path, help="Dossier racine de l'instance (ex: .)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create-user", help="Créer un compte")
    p_create.add_argument("username")
    p_create.add_argument("--role", choices=["admin", "user"], default="user")

    p_pass = sub.add_parser("set-password", help="Changer le mot de passe d'un compte")
    p_pass.add_argument("username")

    sub.add_parser("list-users", help="Lister les comptes")

    p_delete = sub.add_parser("delete-user", help="Supprimer un compte")
    p_delete.add_argument("username")

    args = parser.parse_args()

    if args.command == "create-user":
        password = getpass.getpass("Mot de passe : ")
        create_user(args.instance_dir, args.username, password, role=args.role)
        print(f"Compte « {args.username} » créé (rôle : {args.role}).")
    elif args.command == "set-password":
        password = getpass.getpass("Nouveau mot de passe : ")
        set_password(args.instance_dir, args.username, password)
        print(f"Mot de passe mis à jour pour « {args.username} ».")
    elif args.command == "list-users":
        for u in list_users(args.instance_dir):
            print(f"{u['username']:20s} {u['role']:6s} {u['patientCount']} patient(s) affecté(s)")
    elif args.command == "delete-user":
        delete_user(args.instance_dir, args.username)
        print(f"Compte « {args.username} » supprimé.")


if __name__ == "__main__":
    _cli()
