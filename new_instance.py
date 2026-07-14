"""
Crée une nouvelle instance de l'application (un jeu de données + ses
comptes, destinée à tourner sur son propre port).

    python new_instance.py cardiologie --port 8001
    python new_instance.py cardiologie --port 8001 --demo   # jeu de données fictif, pour tester

Une instance = un dossier instances/<nom>/ contenant :
    data/    tables Excel de référence (patients.xlsx, sejours.xlsx, …)
             + le sous-dossier annotations/ (un CSV par relecteur)
    .auth/   credentials.yaml (comptes, mots de passe hachés, affectations)

Le script crée aussi le premier compte administrateur de l'instance (mot de
passe saisi de façon masquée) et enregistre l'instance dans instances.json,
lu ensuite par launch_all.ps1 pour démarrer toutes les instances en une fois.
"""
import argparse
import getpass
import json
from pathlib import Path

import auth_store

ROOT = Path(__file__).parent
MANIFEST_PATH = ROOT / "instances.json"

# Doit rester synchronisé avec TABLE_NAMES dans main.py.
REQUIRED_TABLES = ["patients", "sejours", "parcours", "documents", "fiches", "observations",
                   "constantes", "biologie", "medicaments", "administrations",
                   "codes_valides", "suggestions"]


def _load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name", help="Nom court de l'instance (ex : cardiologie)")
    parser.add_argument("--port", type=int, required=True, help="Port dédié à cette instance")
    parser.add_argument("--demo", action="store_true",
                         help="Remplit data/ avec le jeu de données fictif de generate_sample_data.py")
    parser.add_argument("--admin-user", help="Identifiant admin (sinon demandé interactivement)")
    parser.add_argument("--admin-password", help="Mot de passe admin (sinon demandé interactivement, masqué)")
    args = parser.parse_args()

    manifest = _load_manifest()
    if args.name in manifest:
        raise SystemExit(f"Une instance « {args.name} » existe déjà dans instances.json")
    if any(e["port"] == args.port for e in manifest.values()):
        raise SystemExit(f"Le port {args.port} est déjà utilisé par une autre instance")

    instance_dir = ROOT / "instances" / args.name
    data_dir = instance_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=False)
    (data_dir / "annotations").mkdir()

    if args.demo:
        import generate_sample_data
        for table_name, df in generate_sample_data.build_tables().items():
            df.to_excel(data_dir / f"{table_name}.xlsx", index=False)
        print(f"Données de démonstration générées dans {data_dir}")
    else:
        print(f"Dossier {data_dir} créé, vide.")
        print("Déposez-y vos fichiers de référence avant de démarrer l'instance :")
        for t in REQUIRED_TABLES:
            print(f"    {t}.xlsx")

    print(f"\nPremier compte administrateur de l'instance « {args.name} » :")
    admin_username = args.admin_user or input("  Identifiant admin : ").strip()
    admin_password = args.admin_password or getpass.getpass("  Mot de passe : ")
    auth_store.create_user(instance_dir, admin_username, admin_password, role="admin")

    # Toujours au format POSIX (/) dans le manifeste, même généré sous Windows :
    # instances.json doit rester utilisable tel quel par launch_all.sh sur Ubuntu.
    rel_dir = instance_dir.relative_to(ROOT).as_posix()
    manifest[args.name] = {"port": args.port, "dir": rel_dir}
    _save_manifest(manifest)

    print(f"\nInstance « {args.name} » enregistrée (port {args.port}) dans instances.json.")
    print("Pour la lancer seule :")
    print(f'    DOSSIER_INSTANCE_DIR="{rel_dir}" python3 -m uvicorn main:app --host 0.0.0.0 --port {args.port}'
          "   # Linux/macOS")
    print(f'    $env:DOSSIER_INSTANCE_DIR = "{rel_dir}"; python -m uvicorn main:app --host 0.0.0.0 --port {args.port}'
          "   # Windows")
    print("Pour lancer toutes les instances enregistrées d'un coup :")
    print("    ./launch_all.sh      (Linux/macOS)")
    print("    .\\launch_all.ps1    (Windows)")


if __name__ == "__main__":
    main()
