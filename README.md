# Dossier patient — recherche & codage (annotation multi-utilisateurs)

Cette version garde **votre prototype HTML/CSS/JS quasiment tel quel**
(mêmes styles, même rendu — bento, rail de navigation, chatbot, recherche…)
et lui branche un petit backend Python (FastAPI) qui :

- lit les données de référence depuis des fichiers **Excel** (lecture seule)
- écrit chaque décision d'annotation dans un **CSV propre à chaque utilisateur**

C'est la différence avec la première version (Streamlit) : ici l'interface
visuelle reste exactement celle de votre maquette, seul le "câblage" des
données change (fetch réseau au lieu de données codées en dur en mémoire JS).

## Lancer l'application

```bash
pip install -r requirements.txt
python generate_sample_data.py      # génère les données de référence (une fois)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Puis ouvrez `http://localhost:8000` (ou l'IP de la machine sur le réseau
local pour que plusieurs personnes s'y connectent). Au premier chargement,
un prompt demande le nom de l'annotateur — il est retenu ensuite dans le
navigateur (`localStorage`) donc pas besoin de le retaper à chaque visite.

## Ce qui a changé dans `static/index.html` par rapport à votre prototype

Uniquement le "câblage données", rien côté visuel :

1. L'objet `PATIENTS` codé en dur a été vidé (`let PATIENTS = {};`) : il est
   maintenant rempli au chargement via `fetch("/api/dossier/...")`.
2. Un petit bloc `boot()` en bas du fichier demande le nom de l'annotateur,
   charge la liste des patients puis leurs dossiers, et lance `render()`
   (au lieu de l'appel `render()` immédiat sur données statiques).
3. Chaque action qui modifiait l'état en mémoire (valider/rejeter/modifier
   une suggestion, supprimer/restaurer/modifier un code validé, ajouter un
   code manuel) appelle en plus `postAnnotation(...)`, qui envoie la décision
   au backend (`POST /api/annotate`) — en parallèle de la mise à jour visuelle
   instantanée déjà présente dans votre code.

Tout le reste (CSS, structure des `render...()`, recherche, bento, chatbot,
gestion des clics) est inchangé.

## API exposée par le backend (`main.py`)

| Route                              | Rôle                                                         |
|-------------------------------------|---------------------------------------------------------------|
| `GET /api/patients`                 | liste des identifiants patients                                |
| `GET /api/dossier/{id}?user=...`    | dossier complet, avec les codes/suggestions déjà fusionnés avec les décisions passées de cet utilisateur |
| `POST /api/annotate`                | enregistre une décision d'annotation                            |
| `GET /api/export`                   | CSV consolidé de toutes les annotations, tous utilisateurs confondus |

## Architecture des données (identique à la logique demandée)

### Excel (lecture seule) dans `data/`
`patients`, `sejours`, `parcours`, `documents`, `constantes`, `biologie`,
`medicaments`, `codes_valides`, `suggestions` — un fichier `.xlsx` par table.
`generate_sample_data.py` reprend les données fictives de votre prototype ;
remplacez-le par votre export réel en gardant les mêmes colonnes.

### CSV (écriture) dans `data/annotations/`
Un fichier `annotations_<nom_utilisateur>.csv` par annotateur → aucune
écriture concurrente possible même si plusieurs personnes valident des
codes en même temps. Colonnes : `timestamp, user, patient_id, sejour_key,
item_type, item_id, action, code, libelle, type_code, commentaire`.

Pour consolider tous les CSV en un seul DataFrame :
```python
import annotations_store as store
df = store.load_all_annotations()
```
(ou directement via `GET /api/export` dans un navigateur / avec `curl`).

## Limites assumées

- Pas d'authentification réelle : le nom saisi au prompt n'est pas vérifié.
  Suffisant pour une petite équipe interne de confiance.
- Le chatbot reste la recherche par mots-clés du prototype d'origine
  (pas un vrai LLM) — à remplacer par un appel à l'API Claude si vous le
  souhaitez, en gardant le même format de réponse `{text, sources}`.
- Si deux annotateurs travaillent en même temps sur le même dossier, ils ne
  voient pas les décisions de l'autre en direct (chacun ne voit que ses
  propres décisions, par design — cf. `data/annotations/`).
