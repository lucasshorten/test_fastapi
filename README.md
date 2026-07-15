# Dossier patient — recherche & codage (annotation multi-utilisateurs)

Cette version garde **votre prototype HTML/CSS/JS quasiment tel quel**
(mêmes styles, même rendu — bento, rail de navigation, chatbot, recherche…)
et lui branche un petit backend Python (FastAPI) qui :

- authentifie chaque relecteur (compte + mot de passe géré par un admin) et
  ne lui montre que les patients qui lui sont affectés
- lit les données de référence depuis des fichiers **Excel** (lecture seule)
- écrit chaque décision d'annotation dans un **CSV propre à chaque utilisateur**

L'app peut tourner en **plusieurs instances indépendantes sur la même
machine**, une par port : chacune a son propre dossier de données, ses
propres comptes, sa propre liste de patients affectés — utile pour séparer
des jeux de données vraiment distincts (services, projets…), chacun avec
ses relecteurs.

## Démarrage rapide (une seule instance)

Pour continuer à travailler avec le dossier `data/` existant, sans passer
par le mécanisme multi-instances :

```bash
pip install -r requirements.txt     # dépendances (une fois)
python generate_sample_data.py      # génère les données de référence (une fois)
python auth_store.py . create-user <votre_nom> --role admin   # premier compte
uvicorn main:app --host 0.0.0.0 --port 8000
```

Si la commande `uvicorn` n'est pas reconnue (fréquent sur Windows si le
dossier `Scripts` de Python n'est pas dans le PATH), utilisez plutôt :

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Puis ouvrez `http://localhost:8000` — vous arrivez sur une page de
connexion. Au premier lancement, si aucun compte n'existe encore, le
serveur l'affiche dans sa sortie console avec la commande à lancer.

Pour arrêter le serveur : `Ctrl+C` dans le terminal où il tourne.

Si vous modifiez `generate_sample_data.py`, relancez-le pour régénérer les
fichiers `.xlsx` dans `data/` — le serveur les relit à chaque redémarrage
(pas besoin de relancer `pip install`).

## Plusieurs instances, plusieurs ports

Chaque instance = un dossier contenant `data/` (tables Excel + annotations)
et `.auth/` (comptes de cette instance, voir plus bas) = un port. Deux
instances ne partagent ni données ni comptes.

**Créer une instance** (ex : un jeu de données "cardiologie") :

```bash
python new_instance.py cardiologie --port 8001
```

Le script crée `instances/cardiologie/data/` (vide — déposez-y vos
`.xlsx` de référence, mêmes colonnes que `generate_sample_data.py`),
demande le premier compte administrateur de cette instance, et
l'enregistre dans `instances.json`. Ajoutez `--demo` pour la remplir avec
le jeu de données fictif à la place (pratique pour tester) :

```bash
python new_instance.py cardiologie --port 8001 --demo
```

**Lancer une instance en particulier :**

```bash
# Linux / macOS
DOSSIER_INSTANCE_DIR="instances/cardiologie" python3 -m uvicorn main:app --host 0.0.0.0 --port 8001
```

```powershell
# Windows
$env:DOSSIER_INSTANCE_DIR = "instances/cardiologie"
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**Lancer toutes les instances enregistrées d'un coup :**

```bash
./launch_all.sh      # Linux / macOS
```

```powershell
.\launch_all.ps1     # Windows
```

Ces scripts lisent `instances.json` et démarrent un process `uvicorn` par
instance, chacun sur son port, en arrière-plan (logs dans
`instances/<nom>/server.out.log` et `server.err.log`). Le manifeste
`instances.json` est toujours écrit avec des chemins au format POSIX (`/`),
utilisable tel quel par les deux scripts quelle que soit la plateforme sur
laquelle une instance a été créée.

## Déploiement pas à pas sur Ubuntu

Étapes pour faire tourner l'app sur un serveur Ubuntu propre (testé sur
Ubuntu 22.04/24.04). `launch_all.sh` est l'équivalent Linux de
`launch_all.ps1`.

**1. Prérequis système**

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

**2. Récupérer le code**

```bash
git clone https://github.com/lucasshorten/test_fastapi.git dossier-patient
cd dossier-patient
```

(ou `scp -r` le dossier depuis votre machine si vous ne passez pas par Git.)

**3. Environnement virtuel et dépendances**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.venv/` est à recréer sur chaque machine — ne pas le copier depuis Windows,
ne pas le committer (déjà exclu par `.gitignore`).

**4. Rendre les scripts exécutables** (le bit d'exécution ne survit pas
toujours à un `git clone` selon l'origine du dépôt) :

```bash
chmod +x launch_all.sh
```

**5. Créer au moins une instance**

Pour un jeu de données réel, sur son propre port :

```bash
python new_instance.py cardiologie --port 8001
# Déposez ensuite vos .xlsx de référence dans instances/cardiologie/data/
```

Ou, pour vérifier rapidement que tout fonctionne avec des données fictives :

```bash
python new_instance.py demo --port 8001 --demo
```

Dans les deux cas, le script demande interactivement l'identifiant et le
mot de passe du premier compte administrateur de cette instance.

Répétez cette étape pour chaque jeu de données distinct à héberger sur ce
serveur (un port différent à chaque fois).

**6. Lancer toutes les instances enregistrées**

```bash
./launch_all.sh
```

Chaque instance tourne en arrière-plan via `nohup` : elle continue de
tourner même après la fermeture de la session SSH. Les logs sont dans
`instances/<nom>/server.out.log` et `server.err.log`.

**7. Vérifier**

```bash
curl -I http://localhost:8001/login.html   # doit répondre 200
pgrep -fa "uvicorn main:app"               # liste les process lancés
```

**8. Ouvrir le port dans le pare-feu**, si `ufw` est actif :

```bash
sudo ufw allow 8001/tcp   # un par instance déployée
```

**9. Arrêter les instances**

```bash
pkill -f "uvicorn main:app"
```

**Pour survivre à un redémarrage du serveur** (au-delà de `nohup`, qui ne
protège que d'une déconnexion SSH) : ajoutez un service `systemd` par
instance qui exécute `launch_all.sh`, ou plus simplement une entrée
`@reboot` dans `crontab -e` :

```
@reboot cd /chemin/vers/dossier-patient && ./launch_all.sh
```

## Comptes, authentification et affectations

Chaque instance gère ses comptes dans `<instance>/.auth/credentials.yaml`
— un fichier, pas une base de données, sur le modèle de `.streamlit/` :
lisible/récupérable à la main en cas de besoin, mais **jamais édité
directement** en pratique puisque le panneau d'administration s'en charge.
Les mots de passe y sont hachés (PBKDF2-HMAC-SHA256), jamais en clair.

- **Connexion** : `/login.html` (identifiant + mot de passe). La session
  dure 12h, portée par un cookie signé — pas de table de sessions à purger.
- **Panneau admin** : `/admin.html`, réservé aux comptes de rôle `admin`.
  Permet de créer/supprimer des comptes, changer un mot de passe, et
  choisir la liste de patients affectés à chaque relecteur (cases à cocher
  filtrables). Un lien "⚙ Admin" apparaît automatiquement dans l'app pour
  les administrateurs.
- **Un relecteur** (`role: user`) ne voit que les patients qui lui sont
  affectés — `/api/patients` et `/api/dossier/{id}` sont filtrés côté
  serveur, pas seulement côté affichage.
- **Un administrateur** voit tous les patients de son instance et peut
  exporter toutes les annotations (`/api/export`).
- Gestion en ligne de commande possible sans passer par le panneau admin :
  `python auth_store.py <dossier_instance> create-user|set-password|list-users|delete-user …`

Le dernier compte administrateur d'une instance ne peut être ni supprimé
ni rétrogradé, pour éviter de se retrouver bloqué dehors.

## Ce qui a changé dans `static/index.html` par rapport à votre prototype

Uniquement le "câblage données" et l'authentification, rien côté visuel :

1. L'objet `PATIENTS` codé en dur a été vidé (`let PATIENTS = {};`) : il est
   maintenant rempli au chargement via `fetch("/api/dossier/...")`.
2. `boot()` vérifie la session (`/api/me`) ; si absente, redirige vers
   `/login.html`. Sinon, charge la liste des patients (déjà filtrée par le
   serveur selon le compte connecté) puis leurs dossiers, et lance
   `render()`. La barre supérieure affiche, à droite du bloc de navigation
   patient, un badge compact avec l'utilisateur connecté, son rôle, un lien
   ⚙ vers l'admin (si applicable) et un bouton ⇄ pour changer de compte
   (déconnexion + retour à `/login.html`).
3. Chaque action qui modifiait l'état en mémoire (valider/rejeter/modifier
   une suggestion, supprimer/restaurer/modifier un code validé, ajouter un
   code manuel) appelle en plus `postAnnotation(...)`, qui envoie la décision
   au backend (`POST /api/annotate`, l'identité vient de la session, plus
   besoin de la transmettre) — en parallèle de la mise à jour visuelle
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
| `POST /api/login`                   | authentification (identifiant + mot de passe), pose le cookie de session |
| `POST /api/logout`                  | efface le cookie de session                                    |
| `GET /api/me`                       | identité et rôle du compte connecté                             |
| `GET /api/patients`                 | liste des patients visibles par le compte connecté (filtrée par affectation, sauf admin) |
| `GET /api/dossier/{id}`             | dossier complet du patient, avec les codes/suggestions déjà fusionnés avec les décisions passées de cet utilisateur — 403 si le patient n'est pas affecté |
| `POST /api/annotate`                | enregistre une décision d'annotation pour le compte connecté    |
| `GET /api/export`                   | CSV consolidé de toutes les annotations, tous utilisateurs confondus (admin uniquement) |
| `GET/POST /api/admin/users`         | lister / créer des comptes (admin uniquement)                   |
| `PUT/DELETE /api/admin/users/{u}`   | modifier (mot de passe, rôle, affectations) / supprimer un compte (admin uniquement) |
| `GET /api/admin/patients`           | liste des patients de l'instance, pour l'écran d'affectation (admin uniquement) |
| `GET /api/rules`                    | dictionnaire des règles de détection des suggestions IA (partagé entre tous les comptes) |
| `PUT /api/rules/{id}`               | modifier le titre/la description d'une règle                    |
| `POST /api/rules/{id}/comments`     | ajouter un commentaire sur une règle                             |

## Architecture des données (identique à la logique demandée)

### Excel (lecture seule) dans `<instance>/data/`
`patients`, `sejours`, `parcours`, `documents`, `fiches`, `observations`,
`constantes`, `biologie`, `medicaments`, `administrations`, `codes_valides`,
`suggestions` — un fichier `.xlsx` par table. `fiches` a une ligne par champ
de formulaire (regroupées par `fiche_id`) et `administrations` une ligne par
prise de médicament effective (générée automatiquement à partir de la
fréquence de chaque médicament — voir `generate_sample_data.py`).
`generate_sample_data.py` reprend les données fictives de votre prototype ;
remplacez-le par votre export réel en gardant les mêmes colonnes.

Aucune table ne conserve de nom d'intervenant (médecin, IDE,
kinésithérapeute...) : ce ne sont pas des colonnes nécessaires au codage et
elles ne doivent pas être exportées.

Le backend (`main.py`) tolère un export réel incomplet : un fichier
`.xlsx` absent ou totalement vide devient une table vide (pas de crash au
démarrage), et une ligne qui ne se rattache à aucun patient/séjour
(`patient_id` ou `sejour_key` manquant) est simplement ignorée plutôt que de
faire planter la construction d'un dossier. Un patient sans aucun séjour
valide s'affiche normalement dans la liste, avec un message « Aucun séjour
enregistré » à la place du dossier.

### CSV (écriture) dans `<instance>/data/annotations/`
Un fichier `annotations_<nom_utilisateur>.csv` par annotateur → aucune
écriture concurrente possible même si plusieurs personnes valident des
codes en même temps. Colonnes : `timestamp, user, patient_id, sejour_key,
item_type, item_id, action, code, libelle, type_code, commentaire`.

Pour consolider tous les CSV d'une instance en un seul DataFrame :
```python
import annotations_store as store
df = store.load_all_annotations(Path("instances/cardiologie/data"))
```
(ou directement via `GET /api/export` dans un navigateur / avec `curl`,
connecté avec un compte admin).

### YAML (comptes) dans `<instance>/.auth/credentials.yaml`
Comptes, mots de passe hachés et patients affectés à chaque relecteur —
voir la section « Comptes, authentification et affectations » ci-dessus.

### YAML (règles IA) dans `<instance>/data/rules.yaml`
Dictionnaire des règles/algorithmes de détection utilisés pour générer les
suggestions de codage, accessible via le bouton « ℹ️ Règles » à côté de
« Suggestion » dans le panneau de codage. Partagé entre tous les comptes de
l'instance (contrairement aux annotations), généré avec des règles par
défaut au premier accès s'il n'existe pas encore. Modifier une règle ou
ajouter un commentaire est purement documentaire : ça ne change jamais les
suggestions déjà générées pour les séjours en cours.

Chaque règle a un identifiant stable (`RG-01`, `RG-02`...), affiché dans la
pop-up, et rattaché à un ou plusieurs codes (CIM-10/CCAM) exprimés en
logique factuelle « SI … ALORS … » (antécédents, codes ATC de médicament,
regex sur le texte, seuils biologiques, actes du parcours, lexiques de
mots-clés). La colonne `regle_id` de `suggestions.xlsx` relie chaque
suggestion affichée dans le panneau de codage à la règle qui l'a produite :
un badge `RG-xx` apparaît sur chaque carte de suggestion, cliquable pour
ouvrir directement la pop-up sur cette règle (recherche pré-remplie,
carte mise en évidence). La barre de recherche de la pop-up filtre par code
**ou** par identifiant (ex. `N18`, `E11`, `RG-04`), en direct et insensible
à la casse.

Au-delà du champ `logique` (texte pour l'humain), chaque règle porte un
champ `parametres` : une liste de conditions structurées
`{champ, operateur, valeur}` (ex. `{"champ": "biologie.dfg", "operateur":
"lt", "valeur": 60}`) pensée pour qu'un script puisse les évaluer sans
reparser du texte libre :

```python
import rules_store
from pathlib import Path

rules = rules_store.load_rules(Path("data"))
for rule in rules:
    for cond in rule["parametres"]:
        ...  # dispatcher sur cond["operateur"] : regex / lt / startswith / wordlist / ...
```

Ce n'est pas un moteur de règles branché sur la génération des suggestions
(volontairement — voir plus haut), juste un format prêt à être consommé par
un futur script d'automatisation.

`rules.yaml` est écrit dans un format pensé pour rester lisible/modifiable
à la main : les champs multi-lignes (`logique`) utilisent le style bloc
YAML (`|`) plutôt que des chaînes repliées entre guillemets, ce qui évite
les apostrophes doublées et les retours à la ligne forcés en plein milieu
d'une phrase.

### Passages surlignés (`highlight`) dans `suggestions.xlsx`
Le passage à surligner dans un document/une fiche/une observation quand on
clique sur la source d'une suggestion (📎) est porté par la suggestion
elle-même (colonne `highlight` de `suggestions.xlsx`), pas par sa source :
une même source (ex. un compte-rendu) peut être citée par plusieurs
suggestions différentes, chacune avec son propre passage pertinent. Vide
(cellule non renseignée) pour les suggestions dont la source est un
événement du parcours, jamais surligné dans l'interface. En dehors d'un clic
sur une suggestion précise, un document/une fiche/une observation affiche
l'ensemble des passages de toutes les suggestions qui le citent.

## Limites assumées

- Le chatbot reste la recherche par mots-clés du prototype d'origine
  (pas un vrai LLM) — à remplacer par un appel à l'API Claude si vous le
  souhaitez, en gardant le même format de réponse `{text, sources}`.
- Si deux annotateurs travaillent en même temps sur le même dossier, ils ne
  voient pas les décisions de l'autre en direct (chacun ne voit que ses
  propres décisions, par design — cf. `data/annotations/`).
- Pas de limitation du nombre de tentatives de connexion (acceptable pour
  une petite équipe interne de confiance ; à ajouter avant une exposition
  plus large).
- Le cookie de session n'est pas marqué `secure` : convient à un usage sur
  réseau interne en HTTP. Si l'app est un jour exposée derrière un reverse
  proxy TLS, ajoutez `secure=True` dans `main.py` (`login()`).
- Pas de réinitialisation de mot de passe en libre-service : c'est
  l'administrateur de l'instance qui la fait depuis `/admin.html`.
