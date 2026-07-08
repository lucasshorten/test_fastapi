"""
Génère les fichiers parquet de référence ("données à revoir") à partir des
données fictives reprises du prototype HTML.

En production, remplacez ce script par votre propre pipeline d'export vers
les mêmes fichiers parquet (mêmes noms de colonnes / tables).

Tables produites dans data/ :
    patients.parquet
    sejours.parquet
    parcours.parquet
    documents.parquet
    constantes.parquet
    biologie.parquet
    medicaments.parquet
    codes_valides.parquet   (codage déjà posé par le clinicien, référence)
    suggestions.parquet     (suggestions de codage à valider/rejeter/modifier)
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PATIENTS = {
    "REC-2024-00187": {
        "sexe": "F", "age": 67,
        "sejour_order": ["sej1", "sej0"],
        "sejours": {
            "sej1": {
                "id_sejour": "ID0000123", "service": "Cardiologie",
                "entree": "2024-05-02", "sortie": "2024-05-14",
                "motif": "Décompensation cardiaque globale", "praticien": "Dr Martin",
                "parcours": [
                    ("pe1", "2024-05-02", "08:14", "Admission", "Entrée via urgences", "Dyspnée aiguë de repos, orthopnée.", "Urgences", "Dr Aubert"),
                    ("pe2", "2024-05-02", "14:30", "Mouvement", "Transfert en Cardiologie", "Hospitalisation conventionnelle, surveillance scope.", "Cardiologie — Ch. 214", "Équipe Cardiologie"),
                    ("pe3", "2024-05-03", "09:00", "Acte", "Échocardiographie transthoracique", "FEVG estimée à 30%, hypokinésie globale.", "Plateau technique cardio", "Dr Bianchi"),
                    ("pe4", "2024-05-05", "11:00", "Acte", "Pose de sonde vésicale à demeure", "Surveillance diurèse dans un contexte d'insuffisance rénale aiguë.", "Cardiologie — Ch. 214", "IDE Roussel"),
                    ("pe5", "2024-05-08", "10:00", "Consultation", "Consultation cardiologique de suivi", "Ajustement du traitement diurétique, poids stable.", "Cardiologie", "Dr Martin"),
                    ("pe6", "2024-05-14", "10:00", "Sortie", "Retour à domicile avec HAD", "Sortie avec surveillance infirmière à domicile.", "Cardiologie", "Dr Martin"),
                ],
                "documents": [
                    ("doc1", "2024-05-14", "Compte-rendu d'hospitalisation", "CRH — Séjour Cardiologie", "Dr Martin",
                     "Patiente admise pour décompensation cardiaque globale sur cardiopathie ischémique connue, avec insuffisance rénale aiguë sur chronique stade IIIB. Évolution favorable sous traitement diurétique IV.",
                     "Patiente admise pour décompensation cardiaque globale sur cardiopathie ischémique connue, avec insuffisance rénale aiguë sur chronique stade IIIB. Évolution favorable sous traitement diurétique IV. Le bilan biologique d'entrée retrouvait un NT-proBNP à 5400 ng/L et une créatininémie à 142 µmol/L. L'échocardiographie a confirmé une dysfonction ventriculaire gauche sévère (FEVG 30%). Traitement diurétique intraveineux avec surveillance stricte de la diurèse, permettant une amélioration clinique et biologique progressive. Sortie à domicile avec majoration du traitement de fond et mise en place d'une hospitalisation à domicile (HAD).",
                     "cardiopathie ischémique"),
                    ("doc2", "2024-05-03", "Compte-rendu d'examen", "Échographie cardiaque transthoracique", "Dr Bianchi",
                     "FEVG estimée à 30%, hypokinésie globale. Pas d'épanchement péricardique. Valves sans anomalie significative.",
                     "FEVG estimée à 30%, hypokinésie globale. Pas d'épanchement péricardique. Valves sans anomalie significative. Cinétique globale altérée de façon homogène, sans anomalie segmentaire focale évocatrice d'une séquelle territoriale univoque. Fonction diastolique non évaluable de façon fiable dans ce contexte.",
                     "FEVG estimée à 30%"),
                    ("doc4", "2024-05-08", "Compte-rendu de consultation", "Consultation cardiologie de suivi", "Dr Martin",
                     "Poids stable à 68kg, auscultation pulmonaire libre. Poursuite du traitement, kaliémie basse à surveiller.",
                     "Poids stable à 68kg, auscultation pulmonaire libre. Poursuite du traitement, kaliémie basse à surveiller. Le traitement bêta-bloquant et l'IEC ont été maintenus à dose stable. Surveillance rapprochée du ionogramme prévue en ville dans les 15 jours compte tenu de la kaliémie basse.",
                     "kaliémie basse"),
                ],
                "constantes": [
                    ("02/05", 104, "158/94", "91%", "37.1°C", "72 kg"),
                    ("05/05", 88, "132/80", "95%", "36.8°C", "70 kg"),
                    ("10/05", 76, "124/76", "97%", "36.7°C", "68 kg"),
                    ("14/05", 72, "120/74", "98%", "36.6°C", "68 kg"),
                ],
                "biologie": [
                    ("02/05", "5400 ng/L", "142 µmol/L", "32 mL/min", "38 mg/L", "3.2 mmol/L", "11.8 g/dL", "9.4 G/L", "137 mmol/L", "6.1 mmol/L"),
                    ("05/05", "3100 ng/L", "128 µmol/L", "37 mL/min", "20 mg/L", "3.4 mmol/L", "11.5 g/dL", "8.1 G/L", "138 mmol/L", "5.9 mmol/L"),
                    ("10/05", "1450 ng/L", "110 µmol/L", "44 mL/min", "8 mg/L", "3.9 mmol/L", "11.9 g/dL", "7.2 G/L", "139 mmol/L", "5.7 mmol/L"),
                ],
                "medicaments": [
                    ("m1", "Furosémide", "40mg", "IV", "2x/jour", "Décompensation cardiaque", "Dr Martin", "2024-05-02", None, "en cours"),
                    ("m2", "Ramipril", "5mg", "orale", "1x/jour", "Insuffisance cardiaque", "Dr Martin", "2024-05-06", None, "en cours"),
                    ("m3", "Héparine", "5000UI", "SC", "3x/jour", "Prévention thrombo-embolique", "Dr Aubert", "2024-05-02", "2024-05-10", "arrêté"),
                ],
                "codes_valides": [
                    ("v1", "I50.0", "CIM-10", "Insuffisance cardiaque congestive", "Dr Martin", "2024-05-14", False),
                    ("v2", "N17.9", "CIM-10", "Insuffisance rénale aiguë, sans précision", "Dr Martin", "2024-05-14", False),
                    ("v3", "DEQP003", "CCAM", "Échographie transthoracique du cœur", "Dr Bianchi", "2024-05-03", False),
                ],
                "suggestions": [
                    ("s1", "I25.9", "CIM-10", "Cardiopathie ischémique chronique, sans précision", 92, "document", "doc1",
                     "Le terme « cardiopathie ischémique » a été détecté dans le compte-rendu d'hospitalisation."),
                    ("s2", "N18.3", "CIM-10", "Maladie rénale chronique, stade 3", 78, "document", "doc1",
                     "Mention de « insuffisance rénale aiguë sur chronique stade IIIB » dans le CRH, compatible avec un DFG mesuré à 32-44 mL/min."),
                    ("s3", "JDLD001", "CCAM", "Pose d'une sonde vésicale à demeure", 85, "parcours", "pe4",
                     "Acte identifié dans le parcours de soins le 05/05 (surveillance diurèse)."),
                    ("s4", "E87.6", "CIM-10", "Hypokaliémie", 55, "document", "doc4",
                     "Kaliémie à 3.2-3.4 mmol/L en biologie et mention « kaliémie basse à surveiller » dans le courrier de consultation."),
                ],
            },
            "sej0": {
                "id_sejour": "ID0000098", "service": "Cardiologie",
                "entree": "2023-11-10", "sortie": "2023-11-13",
                "motif": "Bilan de douleur thoracique d'effort", "praticien": "Dr Martin",
                "parcours": [
                    ("pe1", "2023-11-10", "09:00", "Admission", "Entrée programmée — bilan douleur thoracique", "Douleur thoracique d'effort depuis 3 semaines.", "Cardiologie", "Dr Martin"),
                    ("pe2", "2023-11-11", "09:00", "Acte", "Coronarographie diagnostique", "Sténose serrée de l'IVA proximale, pose d'un stent actif.", "Salle de cathétérisme", "Dr Perrot"),
                    ("pe3", "2023-11-13", "10:00", "Sortie", "Retour à domicile", "Sortie sous double antiagrégation plaquettaire.", "Cardiologie", "Dr Martin"),
                ],
                "documents": [
                    ("doc1", "2023-11-11", "Compte-rendu d'examen", "CR Coronarographie", "Dr Perrot",
                     "Sténose serrée de l'artère interventriculaire antérieure proximale, traitée par angioplastie et pose d'un stent actif.",
                     "Sténose serrée de l'artère interventriculaire antérieure proximale, traitée par angioplastie et pose d'un stent actif. Angioplastie réalisée avec succès par voie radiale droite, sans complication au point de ponction. Double antiagrégation plaquettaire instaurée pour une durée de 12 mois.",
                     "stent actif"),
                ],
                "constantes": [
                    ("10/11", 78, "142/88", "97%", "36.8°C", "71 kg"),
                    ("13/11", 70, "128/80", "98%", "36.6°C", "71 kg"),
                ],
                "biologie": [
                    ("10/11", "210 ng/L", "78 µmol/L", "80 mL/min", "4 mg/L", "4.2 mmol/L", "13.1 g/dL", "6.8 G/L", "140 mmol/L", "5.4 mmol/L"),
                ],
                "medicaments": [
                    ("m1", "Aspirine", "75mg", "orale", "1x/jour", "Post-angioplastie", "Dr Perrot", "2023-11-11", None, "en cours"),
                    ("m2", "Clopidogrel", "75mg", "orale", "1x/jour", "Double antiagrégation (12 mois)", "Dr Perrot", "2023-11-11", "2024-11-11", "en cours"),
                ],
                "codes_valides": [
                    ("v1", "I25.1", "CIM-10", "Maladie coronarienne athéroscléreuse", "Dr Perrot", "2023-11-11", False),
                ],
                "suggestions": [
                    ("s1", "DDAF004", "CCAM", "Angioplastie coronaire avec pose d'endoprothèse", 89, "document", "doc1",
                     "Pose d'un stent actif mentionnée dans le compte-rendu de coronarographie."),
                ],
            },
        },
    },

    "REC-2024-00099": {
        "sexe": "F", "age": 52,
        "sejour_order": ["sej1", "sej0"],
        "sejours": {
            "sej1": {
                "id_sejour": "ID0000201", "service": "Pneumologie",
                "entree": "2024-04-10", "sortie": "2024-04-16",
                "motif": "Pneumopathie aiguë communautaire", "praticien": "Dr Nguyen",
                "parcours": [
                    ("pe1", "2024-04-10", "20:10", "Admission", "Entrée via urgences", "Fièvre à 39.2°C, toux productive, douleur basithoracique droite.", "Urgences", "Dr Caron"),
                    ("pe2", "2024-04-10", "21:00", "Acte", "Radiographie thoracique", "Recherche d'un foyer infectieux.", "Imagerie", "Dr Roche"),
                    ("pe3", "2024-04-11", "08:00", "Acte", "Antibiothérapie IV initiée", "Amoxicilline-acide clavulanique.", "Pneumologie", "Dr Nguyen"),
                    ("pe4", "2024-04-14", "09:30", "Consultation", "Réévaluation clinique", "Apyrexie depuis 48h, amélioration respiratoire.", "Pneumologie", "Dr Nguyen"),
                    ("pe5", "2024-04-16", "10:00", "Sortie", "Retour à domicile", "Relais par antibiothérapie orale.", "Pneumologie", "Dr Nguyen"),
                ],
                "documents": [
                    ("doc1", "2024-04-16", "Compte-rendu d'hospitalisation", "CRH — Séjour Pneumologie", "Dr Nguyen",
                     "Pneumopathie basale droite d'allure bactérienne, syndrome inflammatoire biologique marqué à l'entrée. Évolution favorable sous antibiothérapie.",
                     "Pneumopathie basale droite d'allure bactérienne, syndrome inflammatoire biologique marqué à l'entrée. Évolution favorable sous antibiothérapie. Hémocultures négatives, antigénurie légionelle et pneumocoque négatives. Antibiothérapie probabiliste par amoxicilline-acide clavulanique avec relais oral à J5, bonne évolution clinique et biologique.",
                     "Pneumopathie basale droite"),
                    ("doc2", "2024-04-10", "Compte-rendu de radiologie", "Radiographie thoracique", "Dr Roche",
                     "Foyer de condensation alvéolaire du lobe inférieur droit, sans épanchement pleural associé.",
                     "Foyer de condensation alvéolaire du lobe inférieur droit, sans épanchement pleural associé. Contrôle radiologique de sortie non réalisé, à prévoir à distance si persistance de symptômes.",
                     "foyer de condensation alvéolaire"),
                ],
                "constantes": [
                    ("10/04", 112, "104/68", "92%", "39.2°C", "61 kg"),
                    ("16/04", 78, "118/74", "97%", "36.9°C", "60 kg"),
                ],
                "biologie": [
                    ("10/04", "90 ng/L", "70 µmol/L", "88 mL/min", "182 mg/L", "3.8 mmol/L", "12.6 g/dL", "14.2 G/L", "136 mmol/L", "6.4 mmol/L"),
                    ("14/04", "80 ng/L", "68 µmol/L", "90 mL/min", "24 mg/L", "4.0 mmol/L", "12.4 g/dL", "8.9 G/L", "138 mmol/L", "5.5 mmol/L"),
                ],
                "medicaments": [
                    ("m1", "Amoxicilline / Ac. clavulanique", "1g/125mg", "IV puis orale", "3x/jour", "Pneumopathie bactérienne", "Dr Nguyen", "2024-04-11", "2024-04-16", "arrêté"),
                ],
                "codes_valides": [
                    ("v1", "J15.9", "CIM-10", "Pneumopathie bactérienne, sans précision", "Dr Nguyen", "2024-04-16", False),
                ],
                "suggestions": [
                    ("s1", "J18.1", "CIM-10", "Pneumopathie lobaire, sans précision", 80, "document", "doc2",
                     "Foyer de condensation alvéolaire lobaire décrit sur la radiographie thoracique."),
                ],
            },
            "sej0": {
                "id_sejour": "ID0000077", "service": "Pneumologie",
                "entree": "2023-03-05", "sortie": "2023-03-09",
                "motif": "Pneumopathie aiguë communautaire (épisode antérieur)", "praticien": "Dr Nguyen",
                "parcours": [
                    ("pe1", "2023-03-05", "18:40", "Admission", "Entrée via urgences", "Fièvre et toux productive depuis 2 jours.", "Urgences", "Dr Caron"),
                    ("pe2", "2023-03-06", "08:30", "Acte", "Radiographie thoracique", "Foyer basal gauche.", "Imagerie", "Dr Roche"),
                    ("pe3", "2023-03-09", "10:00", "Sortie", "Retour à domicile", "Relais antibiothérapie orale.", "Pneumologie", "Dr Nguyen"),
                ],
                "documents": [
                    ("doc1", "2023-03-09", "Compte-rendu d'hospitalisation", "CRH — Séjour Pneumologie (2023)", "Dr Nguyen",
                     "Pneumopathie basale gauche, évolution favorable sous antibiothérapie orale.",
                     "Pneumopathie basale gauche, évolution favorable sous antibiothérapie orale. Évolution rapidement favorable sous antibiothérapie orale d'emblée, sans nécessité d'oxygénothérapie.",
                     "Pneumopathie basale gauche"),
                ],
                "constantes": [
                    ("05/03", 98, "112/70", "94%", "38.6°C", "62 kg"),
                ],
                "biologie": [
                    ("05/03", "85 ng/L", "66 µmol/L", "92 mL/min", "96 mg/L", "3.9 mmol/L", "12.9 g/dL", "12.1 G/L", "137 mmol/L", "5.6 mmol/L"),
                ],
                "medicaments": [
                    ("m1", "Amoxicilline", "1g", "orale", "3x/jour", "Pneumopathie bactérienne", "Dr Nguyen", "2023-03-05", "2023-03-12", "arrêté"),
                ],
                "codes_valides": [
                    ("v1", "J18.9", "CIM-10", "Pneumopathie, sans précision", "Dr Nguyen", "2023-03-09", False),
                ],
                "suggestions": [],
            },
        },
    },

    "REC-2024-00234": {
        "sexe": "M", "age": 74,
        "sejour_order": ["sej1", "sej0"],
        "sejours": {
            "sej1": {
                "id_sejour": "ID0000156", "service": "Chirurgie orthopédique",
                "entree": "2024-06-01", "sortie": "2024-06-07",
                "motif": "Prothèse totale de hanche droite", "praticien": "Dr Lefevre",
                "parcours": [
                    ("pe1", "2024-06-01", "07:30", "Admission", "Entrée en hospitalisation programmée", "Admission la veille de l'intervention, à jeun.", "Chirurgie orthopédique", "Dr Lefevre"),
                    ("pe2", "2024-06-01", "10:00", "Acte", "Pose de prothèse totale de hanche", "Voie d'abord postéro-externe, sans complication peropératoire.", "Bloc opératoire", "Dr Lefevre"),
                    ("pe3", "2024-06-02", "09:00", "Consultation", "Visite post-opératoire J1", "Douleur contrôlée, début de la rééducation.", "Chirurgie orthopédique", "Dr Lefevre"),
                    ("pe4", "2024-06-04", "14:00", "Acte", "Séance de kinésithérapie", "Reprise de l'appui partiel.", "Plateau de rééducation", "Kinésithérapeute Ferry"),
                    ("pe5", "2024-06-07", "11:00", "Sortie", "Sortie vers centre de rééducation", "Transfert en SSR pour poursuite de la rééducation.", "Chirurgie orthopédique", "Dr Lefevre"),
                ],
                "documents": [
                    ("doc1", "2024-06-01", "Compte-rendu opératoire", "CR Opératoire — PTH droite", "Dr Lefevre",
                     "Mise en place d'une prothèse totale de hanche non cimentée, voie postéro-externe, sans incident peropératoire. Pertes sanguines estimées à 250mL.",
                     "Mise en place d'une prothèse totale de hanche non cimentée, voie postéro-externe, sans incident peropératoire. Pertes sanguines estimées à 250mL. Intervention réalisée sous rachianesthésie, durée opératoire de 55 minutes. Aucune transfusion peropératoire nécessaire. Suites immédiates simples.",
                     "prothèse totale de hanche"),
                    ("doc2", "2024-06-07", "Compte-rendu de sortie", "Lettre de sortie", "Dr Lefevre",
                     "Patient sortant avec appui partiel, traitement antalgique et anticoagulant préventif pendant 35 jours.",
                     "Patient sortant avec appui partiel, traitement antalgique et anticoagulant préventif pendant 35 jours. Consignes de rééducation transmises au centre de SSR, avec limitation de la flexion de hanche au-delà de 90° pendant 6 semaines.",
                     "anticoagulant préventif"),
                ],
                "constantes": [
                    ("01/06", 82, "138/86", "96%", "37.4°C", "84 kg"),
                    ("07/06", 74, "128/78", "97%", "36.8°C", "83 kg"),
                ],
                "biologie": [
                    ("01/06", "180 ng/L", "88 µmol/L", "72 mL/min", "6 mg/L", "4.1 mmol/L", "13.8 g/dL", "7.6 G/L", "140 mmol/L", "5.8 mmol/L"),
                    ("06/06", "160 ng/L", "84 µmol/L", "75 mL/min", "58 mg/L", "4.0 mmol/L", "10.9 g/dL", "9.8 G/L", "139 mmol/L", "6.0 mmol/L"),
                ],
                "medicaments": [
                    ("m1", "Rivaroxaban", "10mg", "orale", "1x/jour", "Prévention thrombo-embolique post-PTH", "Dr Lefevre", "2024-06-01", None, "en cours"),
                    ("m2", "Paracétamol", "1g", "orale", "4x/jour", "Antalgie post-opératoire", "Dr Lefevre", "2024-06-01", "2024-06-07", "arrêté"),
                ],
                "codes_valides": [
                    ("v1", "NEQK002", "CCAM", "Arthroplastie totale de hanche par voie postéro-externe", "Dr Lefevre", "2024-06-01", False),
                ],
                "suggestions": [
                    ("s1", "Z96.6", "CIM-10", "Présence d'implant articulaire", 88, "document", "doc1",
                     "Pose d'une prothèse totale de hanche mentionnée dans le compte-rendu opératoire."),
                    ("s2", "M16.1", "CIM-10", "Coxarthrose primaire, autre", 66, "parcours", "pe1",
                     "Hospitalisation programmée pour pose de prothèse de hanche, suggérant une coxarthrose sous-jacente."),
                ],
            },
            "sej0": {
                "id_sejour": "ID0000142", "service": "Chirurgie orthopédique",
                "entree": "2024-05-15", "sortie": "2024-05-15",
                "motif": "Bilan pré-opératoire prothèse de hanche", "praticien": "Dr Lefevre",
                "parcours": [
                    ("pe1", "2024-05-15", "09:00", "Consultation", "Consultation chirurgicale", "Indication opératoire retenue, bilan pré-anesthésique programmé.", "Consultation ortho", "Dr Lefevre"),
                    ("pe2", "2024-05-15", "10:30", "Acte", "Radiographie du bassin", "Coxarthrose sévère droite confirmée.", "Imagerie", "Dr Roche"),
                ],
                "documents": [
                    ("doc1", "2024-05-15", "Compte-rendu de consultation", "CR Consultation pré-opératoire", "Dr Lefevre",
                     "Coxarthrose évoluée symptomatique, indication de prothèse totale de hanche retenue.",
                     "Coxarthrose évoluée symptomatique, indication de prothèse totale de hanche retenue. Bilan pré-anesthésique programmé, absence de contre-indication à l'intervention à ce stade.",
                     "prothèse totale de hanche"),
                ],
                "constantes": [
                    ("15/05", 80, "136/84", "97%", "36.7°C", "85 kg"),
                ],
                "biologie": [
                    ("15/05", "170 ng/L", "86 µmol/L", "74 mL/min", "3 mg/L", "4.2 mmol/L", "14.1 g/dL", "6.9 G/L", "141 mmol/L", "5.6 mmol/L"),
                ],
                "medicaments": [],
                "codes_valides": [],
                "suggestions": [
                    ("s1", "M16.1", "CIM-10", "Coxarthrose primaire, autre", 72, "document", "doc1",
                     "Coxarthrose évoluée symptomatique mentionnée dans le compte-rendu de consultation."),
                ],
            },
        },
    },
}


def build_tables():
    patients_rows, sejours_rows = [], []
    parcours_rows, documents_rows = [], []
    constantes_rows, biologie_rows = [], []
    medicaments_rows, codes_valides_rows, suggestions_rows = [], [], []

    for patient_id, p in PATIENTS.items():
        patients_rows.append({"patient_id": patient_id, "sexe": p["sexe"], "age": p["age"]})

        for ordre, sejour_key in enumerate(p["sejour_order"]):
            s = p["sejours"][sejour_key]
            sejours_rows.append({
                "patient_id": patient_id, "sejour_key": sejour_key, "ordre": ordre,
                "id_sejour": s["id_sejour"], "service": s["service"],
                "entree": s["entree"], "sortie": s["sortie"],
                "motif": s["motif"], "praticien": s["praticien"],
            })

            for (eid, date, heure, typ, titre, detail, lieu, acteur) in s["parcours"]:
                parcours_rows.append({
                    "patient_id": patient_id, "sejour_key": sejour_key, "event_id": eid,
                    "date": date, "heure": heure, "type": typ, "titre": titre,
                    "detail": detail, "lieu": lieu, "acteur": acteur,
                })

            for (did, date, typ, titre, auteur, excerpt, full_text, highlight) in s["documents"]:
                documents_rows.append({
                    "patient_id": patient_id, "sejour_key": sejour_key, "doc_id": did,
                    "date": date, "type": typ, "titre": titre, "auteur": auteur,
                    "excerpt": excerpt, "full_text": full_text, "highlight": highlight,
                })

            for (date, fc, ta, spo2, temp, poids) in s["constantes"]:
                constantes_rows.append({
                    "patient_id": patient_id, "sejour_key": sejour_key, "date": date,
                    "fc": fc, "ta": ta, "spo2": spo2, "temp": temp, "poids": poids,
                })

            for (date, ntprobnp, creat, dfg, crp, k, hb, leuco, na, glycemie) in s["biologie"]:
                biologie_rows.append({
                    "patient_id": patient_id, "sejour_key": sejour_key, "date": date,
                    "ntprobnp": ntprobnp, "creat": creat, "dfg": dfg, "crp": crp,
                    "k": k, "hb": hb, "leuco": leuco, "na": na, "glycemie": glycemie,
                })

            for (mid, nom, dose, voie, freq, indication, prescripteur, debut, fin, statut) in s["medicaments"]:
                medicaments_rows.append({
                    "patient_id": patient_id, "sejour_key": sejour_key, "med_id": mid,
                    "nom": nom, "dose": dose, "voie": voie, "frequence": freq,
                    "indication": indication, "prescripteur": prescripteur,
                    "debut": debut, "fin": fin, "statut": statut,
                })

            for (cid, code, typ, libelle, note_par, date, removed) in s["codes_valides"]:
                codes_valides_rows.append({
                    "patient_id": patient_id, "sejour_key": sejour_key, "code_id": cid,
                    "code": code, "type": typ, "libelle": libelle,
                    "note_par": note_par, "date": date, "removed": removed,
                })

            for (sid, code, typ, libelle, confiance, src_kind, src_id, justification) in s["suggestions"]:
                suggestions_rows.append({
                    "patient_id": patient_id, "sejour_key": sejour_key, "suggestion_id": sid,
                    "code": code, "type": typ, "libelle": libelle, "confiance": confiance,
                    "source_kind": src_kind, "source_id": src_id, "justification": justification,
                })

    return {
        "patients": pd.DataFrame(patients_rows),
        "sejours": pd.DataFrame(sejours_rows),
        "parcours": pd.DataFrame(parcours_rows),
        "documents": pd.DataFrame(documents_rows),
        "constantes": pd.DataFrame(constantes_rows),
        "biologie": pd.DataFrame(biologie_rows),
        "medicaments": pd.DataFrame(medicaments_rows),
        "codes_valides": pd.DataFrame(codes_valides_rows),
        "suggestions": pd.DataFrame(suggestions_rows),
    }


if __name__ == "__main__":
    tables = build_tables()
    for name, df in tables.items():
        path = DATA_DIR / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  {name:15s} -> {path}  ({len(df)} lignes)")
    print("\nDonnées de référence générées dans", DATA_DIR)
