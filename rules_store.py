"""
Dictionnaire des règles/algorithmes utilisés pour générer les suggestions de
codage — partagé entre tous les utilisateurs d'une instance (contrairement
aux annotations, qui restent propres à chaque relecteur).

Un fichier YAML par instance : <data_dir>/rules.yaml, à côté des tables
Excel de référence. Modifier une règle ou ajouter un commentaire est
purement documentaire : ça n'affecte jamais les suggestions déjà générées
(pas de lien vers la logique de génération, volontairement).
"""
import secrets
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Chaque règle porte un identifiant stable "RG-xx" (utilisé comme clé d'API,
# affiché à l'écran, et cliquable depuis une suggestion pour ouvrir cette
# règle précise). Le champ "parametres" est la version machine-lisible de
# "logique" : une liste de conditions ET-combinées, chacune de la forme
# {champ, operateur, valeur[, flags]} — pensée pour qu'un script Python
# puisse itérer dessus sans avoir à reparser du texte libre (voir le README
# pour un exemple d'évaluation).
DEFAULT_RULES = [
    {
        "id": "RG-01",
        "titre": "Antécédent codé lors d'un séjour précédent",
        "categorie": "Antécédent",
        "logique": (
            "SI un code CIM-10 figure dans les codes validés d'un séjour antérieur "
            "du même patient\n"
            "ALORS reproposer ce même code pour le séjour en cours"
        ),
        "parametres": [
            {"champ": "codes_valides.code", "operateur": "present_in_prior_sejour", "valeur": None},
        ],
        "code": "E11.9",
        "libelle": "Diabète de type 2, sans complication (exemple)",
        "type": "CIM-10",
        "description": (
            "Un diagnostic chronique déjà validé par un clinicien lors d'un séjour "
            "précédent (diabète, insuffisance cardiaque, coronaropathie...) reste "
            "pertinent : on le repropose pour le séjour en cours. Exemple concret : "
            "si E11.x a été validé lors d'un séjour antérieur, le patient a été "
            "diabétique — on peut le recoder comme tel, sous réserve de "
            "confirmation par le relecteur. Règle générique : le code rejoué est "
            "celui trouvé dans l'antécédent, pas un code fixe."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-02",
        "titre": "Insulinothérapie pendant le séjour",
        "categorie": "Médicament",
        "logique": (
            "SI un médicament administré a un code ATC commençant par A10 "
            "(insulines et analogues)\n"
            "ALORS suggérer E11.9"
        ),
        "parametres": [
            {"champ": "medicaments.atc", "operateur": "startswith", "valeur": "A10"},
        ],
        "code": "E11.9",
        "libelle": "Diabète de type 2, sans complication",
        "type": "CIM-10",
        "description": (
            "La prescription d'insuline pendant le séjour est un signal fort de "
            "diabète, même si le diagnostic n'a été formulé dans aucun "
            "compte-rendu. Le code ATC du médicament (pas seulement son nom "
            "commercial) est utilisé pour rester robuste aux génériques. "
            "Nécessite une colonne `atc` sur la table medicaments (absente du "
            "jeu de données fictif actuel — voir README)."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-03",
        "titre": "Double antiagrégation après pose de stent",
        "categorie": "Médicament",
        "logique": (
            "SI médicament ATC B01AC (clopidogrel, ticagrélor...) prescrit en "
            "association avec l'aspirine\n"
            "ET un acte de pose d'endoprothèse coronaire figure dans le parcours\n"
            "ALORS suggérer Z95.5"
        ),
        "parametres": [
            {"champ": "medicaments.atc", "operateur": "startswith", "valeur": "B01AC"},
            {"champ": "parcours.titre", "operateur": "regex", "valeur": "endoproth[eè]se coronaire|pose.*stent", "flags": "i"},
        ],
        "code": "Z95.5",
        "libelle": "Présence d'un implant et d'une greffe cardiaques et vasculaires — endoprothèse coronaire",
        "type": "CIM-10",
        "description": (
            "La combinaison des deux antiagrégants plaquettaires est le traitement "
            "standard après pose de stent : la détecter en même temps que l'acte "
            "de pose confirme la présence de l'implant, utile même longtemps après "
            "l'intervention initiale."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-04",
        "titre": "Mention de cardiopathie ischémique",
        "categorie": "Mots-clés",
        "logique": (
            "SI un document du séjour matche la regex\n"
            "/cardiopath(?:ie)?\\s+isch[ée]miqu\\w*/i\n"
            "ALORS suggérer I25.9"
        ),
        "parametres": [
            {"champ": "documents.full_text", "operateur": "regex", "valeur": "cardiopath(?:ie)?\\s+isch[ée]miqu\\w*", "flags": "i"},
        ],
        "code": "I25.9",
        "libelle": "Cardiopathie ischémique chronique, sans précision",
        "type": "CIM-10",
        "description": (
            "Recherche l'expression sur le texte intégral des comptes-rendus "
            "(CRH, consultations, imagerie...), variantes orthographiques "
            "incluses. Un simple mot-clé exact serait trop rigide (« cardiopathies "
            "ischémiques », « cardiopathie ischémique sévère »…) : la regex "
            "capture la racine du terme plutôt qu'une chaîne figée."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-05",
        "titre": "Insuffisance rénale, aiguë ou chronique",
        "categorie": "Mots-clés",
        "logique": (
            "SI un document ou une observation matche la regex\n"
            "/insuffisance\\s+r[ée]nale\\s+(aigu[eë]|chronique)/i\n"
            "ALORS suggérer N17.9 si « aiguë » est détecté, sinon N18.9 si "
            "« chronique » est détecté"
        ),
        "parametres": [
            {"champ": "documents.full_text", "operateur": "regex", "valeur": "insuffisance\\s+r[ée]nale\\s+(aigu[eë]|chronique)", "flags": "i"},
        ],
        "code": "N17.9 / N18.9",
        "libelle": "Insuffisance rénale aiguë, SP / Maladie rénale chronique, SP",
        "type": "CIM-10",
        "description": (
            "Le qualificatif capturé par la regex (aiguë vs chronique) détermine "
            "directement quel code est suggéré — pas de suggestion générique "
            "« insuffisance rénale » sans précision du caractère aigu/chronique."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-06",
        "titre": "DFG abaissé → maladie rénale chronique",
        "categorie": "Seuil biologique",
        "logique": (
            "SI DFG < 30 mL/min ALORS suggérer N18.4\n"
            "SI 30 ≤ DFG < 45 mL/min ALORS suggérer N18.3\n"
            "SI 45 ≤ DFG < 60 mL/min ALORS suggérer N18.2"
        ),
        "parametres": [
            {"champ": "biologie.dfg", "operateur": "lt", "valeur": 60},
        ],
        "code": "N18.2 / N18.3 / N18.4",
        "libelle": "Maladie rénale chronique, stade 2 / 3 / 4 selon le DFG mesuré",
        "type": "CIM-10",
        "description": (
            "Le stade suggéré dépend directement de la dernière valeur de DFG "
            "mesurée dans le séjour. Une seule mesure abaissée ne confirme pas "
            "une maladie chronique (elle peut être aiguë) : à confirmer par le "
            "relecteur au vu du contexte clinique. Le seuil de `parametres` "
            "(< 60) déclenche la règle ; le stade précis (2/3/4) reste à choisir "
            "selon la valeur exacte, voir la logique ci-dessus."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-07",
        "titre": "Hypokaliémie",
        "categorie": "Seuil biologique",
        "logique": "SI kaliémie < 3.5 mmol/L\nALORS suggérer E87.6",
        "parametres": [
            {"champ": "biologie.k", "operateur": "lt", "valeur": 3.5},
        ],
        "code": "E87.6",
        "libelle": "Hypokaliémie",
        "type": "CIM-10",
        "description": (
            "Seuil biologique simple, sans condition supplémentaire. La confiance "
            "de la suggestion augmente si une mention textuelle correspondante "
            "(« kaliémie basse », « à surveiller »...) est aussi trouvée dans un "
            "compte-rendu du même séjour."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-08",
        "titre": "Pose de sonde vésicale à demeure",
        "categorie": "Acte",
        "logique": (
            "SI l'intitulé d'un événement du parcours matche la regex\n"
            "/sonde\\s+v[ée]sicale|cath[ée]ter\\s+urinaire/i\n"
            "ALORS suggérer JDLD001"
        ),
        "parametres": [
            {"champ": "parcours.titre", "operateur": "regex", "valeur": "sonde\\s+v[ée]sicale|cath[ée]ter\\s+urinaire", "flags": "i"},
        ],
        "code": "JDLD001",
        "libelle": "Pose d'une sonde vésicale à demeure",
        "type": "CCAM",
        "description": (
            "Détecte l'acte directement dans la chronologie du parcours de soins, "
            "plutôt que dans un compte-rendu — utile pour les actes rarement "
            "détaillés dans un document dédié."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-09",
        "titre": "Lexique clinique générique dans les documents",
        "categorie": "Mots-clés",
        "logique": (
            "SI le texte d'un document (ou le détail d'un événement du parcours) "
            "contient un terme du lexique suivi (liste non exhaustive : « stent "
            "actif », « prothèse totale de hanche », « coxarthrose », « foyer de "
            "condensation alvéolaire »...)\n"
            "ALORS suggérer le code CIM-10/CCAM associé à ce terme dans le lexique"
        ),
        "parametres": [
            {"champ": "documents.full_text", "operateur": "wordlist",
             "valeur": ["stent actif", "prothèse totale de hanche", "coxarthrose",
                        "foyer de condensation alvéolaire"]},
        ],
        "code": "(variable)",
        "libelle": "Dépend du terme détecté — voir le lexique en paramètres",
        "type": "CIM-10",
        "description": (
            "Sert de filet de sécurité pour les diagnostics/actes fréquents qui ne "
            "justifient pas chacun leur propre règle dédiée (contrairement à RG-04 "
            "ou RG-05, qui ciblent un motif précis avec une regex propre). Le "
            "lexique (`parametres[0].valeur`) est la partie à enrichir en premier "
            "quand un nouveau terme récurrent est identifié."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-10",
        "titre": "Mentions dans les fiches de liaison et de suivi",
        "categorie": "Fiche",
        "logique": (
            "SI un champ rempli d'une fiche de liaison/suivi contient un terme du "
            "lexique de dépendance/fonction (ex : « aide pour la toilette », "
            "« toux productive »...)\n"
            "ALORS suggérer le code correspondant"
        ),
        "parametres": [
            {"champ": "fiches.champ_valeur", "operateur": "wordlist",
             "valeur": ["aide pour la toilette", "toux productive"]},
        ],
        "code": "(variable)",
        "libelle": "Dépend du terme détecté — voir le lexique en paramètres",
        "type": "CIM-10",
        "description": (
            "Les fiches de liaison/suivi sont structurées en champs courts "
            "(autonomie, dispositifs, rééducation...) : plus fiables à analyser "
            "qu'un texte libre, mais avec un vocabulaire plus restreint que les "
            "comptes-rendus."
        ),
        "commentaires": [],
    },
    {
        "id": "RG-11",
        "titre": "Mentions dans les observations médicales",
        "categorie": "Observation",
        "logique": (
            "SI le texte d'une observation clinique contient un terme "
            "symptomatique reconnu (ex : « dyspnée », « douleur »...)\n"
            "ALORS suggérer le code de symptôme correspondant"
        ),
        "parametres": [
            {"champ": "observations.texte", "operateur": "wordlist", "valeur": ["dyspnée", "douleur"]},
        ],
        "code": "(variable)",
        "libelle": "Dépend du terme détecté — voir le lexique en paramètres",
        "type": "CIM-10",
        "description": (
            "Recherche des symptômes et signes cliniques mentionnés dans les "
            "observations chronologiques (cliniques, fonctionnelles, sociales) du "
            "dossier — utile quand le symptôme n'apparaît que dans une observation "
            "courte, sans compte-rendu dédié."
        ),
        "commentaires": [],
    },
]


def _rules_path(data_dir: Path) -> Path:
    return Path(data_dir) / "rules.yaml"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(data_dir: Path) -> list[dict]:
    path = _rules_path(data_dir)
    if not path.exists():
        rules = [dict(r, commentaires=list(r["commentaires"])) for r in DEFAULT_RULES]
        _save(data_dir, rules)
        return rules
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return doc.get("rules", [])


def _save(data_dir: Path, rules: list[dict]) -> None:
    path = _rules_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump({"rules": rules}, f, allow_unicode=True, sort_keys=False)


def load_rules(data_dir: Path) -> list[dict]:
    return _load(data_dir)


def update_rule(data_dir: Path, rule_id: str, titre: str | None = None,
                 logique: str | None = None, description: str | None = None,
                 parametres: list | None = None) -> dict:
    """parametres n'est pas exposé dans le formulaire d'édition simple de
    l'interface (qui ne touche que titre/logique/description) — c'est le
    point d'entrée pour un futur script qui ajusterait les conditions
    machine-lisibles d'une règle."""
    rules = _load(data_dir)
    rule = next((r for r in rules if r["id"] == rule_id), None)
    if rule is None:
        raise KeyError(rule_id)
    if titre is not None:
        rule["titre"] = titre
    if logique is not None:
        rule["logique"] = logique
    if description is not None:
        rule["description"] = description
    if parametres is not None:
        rule["parametres"] = parametres
    _save(data_dir, rules)
    return rule


def add_comment(data_dir: Path, rule_id: str, auteur: str, texte: str) -> dict:
    rules = _load(data_dir)
    rule = next((r for r in rules if r["id"] == rule_id), None)
    if rule is None:
        raise KeyError(rule_id)
    comment = {"id": secrets.token_hex(4), "auteur": auteur, "date": _now(), "texte": texte}
    rule.setdefault("commentaires", []).append(comment)
    _save(data_dir, rules)
    return comment
