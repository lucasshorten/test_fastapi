#!/usr/bin/env bash
#
# Démarre une instance uvicorn par entrée de instances.json, chacune sur son
# propre port, avec ses propres données et ses propres comptes
# (DOSSIER_INSTANCE_DIR). Un process Python par instance, tous sur la même
# machine. Équivalent Linux/Ubuntu de launch_all.ps1.
#
# Créez d'abord une instance avec :
#     python3 new_instance.py <nom> --port <port>
#
# Puis lancez tout avec :
#     ./launch_all.sh
#
# Chaque instance écrit ses logs dans instances/<nom>/server.out.log et
# server.err.log. Pour vérifier / arrêter, voir les commandes affichées à
# la fin du script.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$ROOT/instances.json"
PYTHON="${PYTHON:-python3}"

if [[ ! -f "$MANIFEST" ]]; then
  echo "instances.json introuvable — créez d'abord une instance avec new_instance.py" >&2
  exit 1
fi

while IFS=$'\t' read -r name port dir; do
  instance_dir="$ROOT/$dir"
  out_log="$instance_dir/server.out.log"
  err_log="$instance_dir/server.err.log"

  echo "Démarrage de '$name' sur le port $port (données : $dir)…"
  DOSSIER_INSTANCE_DIR="$instance_dir" nohup "$PYTHON" -m uvicorn main:app \
    --host 0.0.0.0 --port "$port" --app-dir "$ROOT" \
    > "$out_log" 2> "$err_log" &
  echo "  PID $! — logs : $out_log / $err_log"
done < <("$PYTHON" - "$MANIFEST" <<'PYEOF' | tr -d '\r'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    manifest = json.load(f)
for name, entry in manifest.items():
    print(f"{name}\t{entry['port']}\t{entry['dir']}")
PYEOF
)

echo
echo "Toutes les instances sont lancées."
echo "Pour vérifier :  pgrep -fa 'uvicorn main:app'"
echo "Pour arrêter :   pkill -f 'uvicorn main:app'"
