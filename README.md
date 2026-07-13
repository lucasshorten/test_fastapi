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

Trois commandes suffisent, à exécuter depuis le dossier du projet :

```bash
pip install -r requirements.txt     # dépendances (une fois)
python generate_sample_data.py      # génère les données de référence (une fois)
uvicorn main:app --host 0.0.0.0 --port 8000
```

Si la commande `uvicorn` n'est pas reconnue (fréquent sur Windows si le
dossier `Scripts` de Python n'est pas dans le PATH), utilisez plutôt :

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Puis ouvrez `http://localhost:8000` (ou l'IP de la machine sur le réseau
local pour que plusieurs personnes s'y connectent). Au premier chargement,
un prompt demande le nom de l'annotateur — il est retenu ensuite dans le
navigateur (`localStorage`) donc pas besoin de le retaper à chaque visite.

Pour arrêter le serveur : `Ctrl+C` dans le terminal où il tourne.

Si vous modifiez `generate_sample_data.py`, relancez-le pour régénérer les
fichiers `.xlsx` dans `data/` — le serveur les relit à chaque redémarrage
(pas besoin de relancer `pip install`).

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

## Évolutions ultérieures de l'interface

Ajoutées après la migration initiale, toujours branchées sur les mêmes
tables Excel / la même API :

- **Onglet Documents** : trois sous-onglets — *Documents*, *Fiches*
  (formulaires de liaison/suivi remplis, relus en lecture seule) et
  *Observations médicales* (récapitulatif chronologique). Chaque élément
  s'affiche sous forme de ligne repliée (titre · date · UF) qu'on déroule en
  cliquant dessus. Un clic sur la source d'une suggestion de codage (📎)
  ouvre directement le bon document/fiche/observation, déroulé, avec le
  passage concerné surligné.
- **Onglet Médicaments** : grille jour par jour (un médicament par ligne, un
  jour par colonne, scrollable horizontalement, nom du médicament fixe à
  gauche) montrant l'heure de chaque prise réellement administrée, avec un
  tableau détaillé de toutes les administrations en dessous.
- **Panneau de codage (à droite)** : rétractable via le bouton ◀/▶, et
  défile indépendamment du reste de la page — la barre supérieure (recherche,
  navigation patient, bandeau des séjours) reste toujours visible.
- **Navigation** : l'onglet ouvert (Résumé/Parcours/Documents/…) et la
  position de la barre des séjours sont conservés en changeant de séjour ou
  de patient.

## API exposée par le backend (`main.py`)

| Route                              | Rôle                                                         |
|-------------------------------------|---------------------------------------------------------------|
| `GET /api/patients`                 | liste des identifiants patients                                |
| `GET /api/dossier/{id}?user=...`    | dossier complet, avec les codes/suggestions déjà fusionnés avec les décisions passées de cet utilisateur |
| `POST /api/annotate`                | enregistre une décision d'annotation                            |
| `GET /api/export`                   | CSV consolidé de toutes les annotations, tous utilisateurs confondus |

## Architecture des données (identique à la logique demandée)

### Excel (lecture seule) dans `data/`
`patients`, `sejours`, `parcours`, `documents`, `fiches`, `observations`,
`constantes`, `biologie`, `medicaments`, `administrations`, `codes_valides`,
`suggestions` — un fichier `.xlsx` par table. `fiches` a une ligne par champ
de formulaire (regroupées par `fiche_id`) et `administrations` une ligne par
prise de médicament effective (générée automatiquement à partir de la
fréquence de chaque médicament — voir `generate_sample_data.py`).
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
