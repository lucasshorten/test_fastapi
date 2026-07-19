"""
Génère les fichiers Excel de référence ("données à revoir") à partir des
données fictives reprises du prototype HTML.

En production, remplacez ce script par votre propre pipeline d'export vers
les mêmes fichiers Excel (mêmes noms de colonnes / tables).

Tables produites dans data/ :
    patients.xlsx
    sejours.xlsx          (id_sejour identifie le séjour, aucune autre clé)
    parcours.xlsx
    documents.xlsx         (peut exister hors séjour : id_sejour vide)
    fiches.xlsx            (fiches de liaison/suivi remplies, une ligne par champ ;
                             peut exister hors séjour : id_sejour vide)
    observations.xlsx      (observations médicales du patient ; peut exister
                             hors séjour : id_sejour vide)
    constantes.xlsx
    biologie.xlsx           (une ligne par mesure : patient_id, id_sejour, date,
                             code, valeur, unite — format long)
    medicaments.xlsx        (une ligne par prise effective de médicament : nom,
                             qté, unité, atc, ucd, date_administration)
    codes_valides.xlsx      (codage déjà posé par le clinicien, référence)
    suggestions.xlsx        (suggestions de codage à valider/rejeter/modifier, portent
                             aussi le passage à surligner dans leur source — voir
                             "highlight" ci-dessous)

Aucune de ces tables ne conserve de nom d'intervenant (médecin, IDE,
kinésithérapeute...) : ce n'est pas nécessaire au codage et ces données sont
retirées avant tout export.
"""
import re
from datetime import date, timedelta

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Code ATC + code UCD (fictifs pour UCD) de chaque médicament utilisé dans le
# jeu de données — une ligne par prise effective porte ces deux codes.
ATC_UCD_BY_DRUG = {
    "Furosémide": ("C03CA01", "9200001"),
    "Ramipril": ("C09AA05", "9200002"),
    "Héparine": ("B01AB01", "9200003"),
    "Aspirine": ("B01AC06", "9200004"),
    "Clopidogrel": ("B01AC04", "9200005"),
    "Amoxicilline / Ac. clavulanique": ("J01CR02", "9200006"),
    "Amoxicilline": ("J01CA04", "9200007"),
    "Rivaroxaban": ("B01AF01", "9200008"),
    "Paracétamol": ("N02BE01", "9200009"),
}

BIOLOGIE_CODES = ["ntprobnp", "creat", "dfg", "crp", "k", "hb", "leuco", "na", "glycemie"]

PATIENTS = {
    "REC-2024-00187": {
        "sexe": "F", "age": 67,
        "sejour_order": ["sej1", "sej0"],
        "sejours": {
            "sej1": {
                "id_sejour": "ID0000123", "service": "Cardiologie",
                "entree": "2024-05-02", "sortie": "2024-05-14",
                "parcours": [
                    ("pe1", "2024-05-02", "08:14", "Admission", "Entrée via urgences", "Dyspnée aiguë de repos, orthopnée.", "UF Urgences"),
                    ("pe2", "2024-05-02", "14:30", "Mouvement", "Transfert en Cardiologie", "Hospitalisation conventionnelle, surveillance scope.", "UF Cardiologie"),
                    ("pe3", "2024-05-03", "09:00", "Acte", "Échocardiographie transthoracique", "FEVG estimée à 30%, hypokinésie globale.", "UF Imagerie cardiaque"),
                    ("pe4", "2024-05-05", "11:00", "Acte", "Pose de sonde vésicale à demeure", "Surveillance diurèse dans un contexte d'insuffisance rénale aiguë.", "UF Cardiologie"),
                    ("pe5", "2024-05-08", "10:00", "Consultation", "Consultation cardiologique de suivi", "Ajustement du traitement diurétique, poids stable.", "UF Cardiologie"),
                    ("pe6", "2024-05-14", "10:00", "Sortie", "Retour à domicile avec HAD", "Sortie avec surveillance infirmière à domicile.", "UF Cardiologie"),
                ],
                "documents": [
                    ("doc1", "2024-05-14", "Compte-rendu d'hospitalisation", "CRH — Séjour Cardiologie", "UF Cardiologie",
                     "Patiente admise pour décompensation cardiaque globale sur cardiopathie ischémique connue, avec insuffisance rénale aiguë sur chronique stade IIIB. Évolution favorable sous traitement diurétique IV.",
                     "Patiente admise pour décompensation cardiaque globale sur cardiopathie ischémique connue, avec insuffisance rénale aiguë sur chronique stade IIIB. Évolution favorable sous traitement diurétique IV. Le bilan biologique d'entrée retrouvait un NT-proBNP à 5400 ng/L et une créatininémie à 142 µmol/L. L'échocardiographie a confirmé une dysfonction ventriculaire gauche sévère (FEVG 30%). Traitement diurétique intraveineux avec surveillance stricte de la diurèse, permettant une amélioration clinique et biologique progressive. Sortie à domicile avec majoration du traitement de fond et mise en place d'une hospitalisation à domicile (HAD)."),
                    ("doc2", "2024-05-03", "Compte-rendu d'examen", "Échographie cardiaque transthoracique", "UF Imagerie cardiaque",
                     "FEVG estimée à 30%, hypokinésie globale. Pas d'épanchement péricardique. Valves sans anomalie significative.",
                     "FEVG estimée à 30%, hypokinésie globale. Pas d'épanchement péricardique. Valves sans anomalie significative. Cinétique globale altérée de façon homogène, sans anomalie segmentaire focale évocatrice d'une séquelle territoriale univoque. Fonction diastolique non évaluable de façon fiable dans ce contexte."),
                    ("doc4", "2024-05-08", "Compte-rendu de consultation", "Consultation cardiologie de suivi", "UF Cardiologie",
                     "Poids stable à 68kg, auscultation pulmonaire libre. Poursuite du traitement, kaliémie basse à surveiller.",
                     "Poids stable à 68kg, auscultation pulmonaire libre. Poursuite du traitement, kaliémie basse à surveiller. Le traitement bêta-bloquant et l'IEC ont été maintenus à dose stable. Surveillance rapprochée du ionogramme prévue en ville dans les 15 jours compte tenu de la kaliémie basse."),
                ],
                "fiches": [
                    ("f1", "Fiche de liaison infirmière", "Liaison IDE", "2024-05-14", "UF Cardiologie", [
                        ("Autonomie", "Aide partielle pour la toilette, marche avec déambulateur"),
                        ("Régime alimentaire", "Sans sel strict"),
                        ("Allergies connues", "Aucune"),
                        ("Personne à prévenir", "Fille — Mme Dubreuil, 06 12 34 56 78"),
                        ("Dispositifs en place", "Voie veineuse périphérique ; sonde vésicale retirée le 12/05"),
                    ]),
                    ("f2", "Fiche de sortie HAD", "Sortie", "2024-05-14", "UF Cardiologie", [
                        ("Structure d'aval", "Hospitalisation à domicile (HAD)"),
                        ("Surveillance prévue", "Poids quotidien, diurèse, ionogramme à J3"),
                        ("Traitement de sortie", "Furosémide 40mg 2x/j, Ramipril 5mg 1x/j"),
                    ]),
                ],
                "observations": [
                    ("o1", "2024-05-02", "UF Cardiologie", "Clinique",
                     "Dyspnée de repos avec orthopnée à l'admission, crépitants bilatéraux aux bases, œdèmes des membres inférieurs."),
                    ("o2", "2024-05-08", "UF Cardiologie", "Fonctionnelle",
                     "Amélioration nette de la dyspnée, périmètre de marche en progression, plus d'orthopnée."),
                    ("o3", "2024-05-14", "UF Cardiologie", "Sociale",
                     "Patiente vivant seule, aide à domicile déjà en place 2x/semaine ; fille disponible pour renfort ponctuel."),
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
                    ("Furosémide", 40, "mg", "2x/jour", "2024-05-02", None),
                    ("Ramipril", 5, "mg", "1x/jour", "2024-05-06", None),
                    ("Héparine", 5000, "UI", "3x/jour", "2024-05-02", "2024-05-10"),
                ],
                "codes_valides": [
                    ("v1", "I50.0", "CIM-10", "Insuffisance cardiaque congestive", "2024-05-14", False),
                    ("v2", "N17.9", "CIM-10", "Insuffisance rénale aiguë, sans précision", "2024-05-14", False),
                    ("v3", "DEQP003", "CCAM", "Échographie transthoracique du cœur", "2024-05-03", False),
                ],
                "suggestions": [
                    ("s1", "I25.9", "CIM-10", "Cardiopathie ischémique chronique, sans précision", 92, "document", "doc1",
                     "Le terme « cardiopathie ischémique » a été détecté dans le compte-rendu d'hospitalisation.", "RG-04",
                     "cardiopathie ischémique"),
                    ("s2", "N18.3", "CIM-10", "Maladie rénale chronique, stade 3", 78, "document", "doc1",
                     "Mention de « insuffisance rénale aiguë sur chronique stade IIIB » dans le CRH, compatible avec un DFG mesuré à 32-44 mL/min.", "RG-06",
                     "insuffisance rénale aiguë sur chronique stade IIIB"),
                    ("s3", "JDLD001", "CCAM", "Pose d'une sonde vésicale à demeure", 85, "parcours", "pe4",
                     "Acte identifié dans le parcours de soins le 05/05 (surveillance diurèse).", "RG-08", None),
                    ("s4", "E87.6", "CIM-10", "Hypokaliémie", 55, "document", "doc4",
                     "Kaliémie à 3.2-3.4 mmol/L en biologie et mention « kaliémie basse à surveiller » dans le courrier de consultation.", "RG-07",
                     "kaliémie basse"),
                    ("s5", "Z74.1", "CIM-10", "Nécessité d'aide pour les soins personnels", 61, "fiche", "f1",
                     "Aide partielle pour la toilette mentionnée dans la fiche de liaison infirmière.", "RG-10",
                     "Aide partielle pour la toilette"),
                    ("s6", "R06.0", "CIM-10", "Dyspnée", 70, "observation", "o1",
                     "Dyspnée de repos avec orthopnée décrite dans l'observation clinique d'entrée.", "RG-11",
                     "Dyspnée de repos avec orthopnée"),
                ],
            },
            "sej0": {
                "id_sejour": "ID0000098", "service": "Cardiologie",
                "entree": "2023-11-10", "sortie": "2023-11-13",
                "parcours": [
                    ("pe1", "2023-11-10", "09:00", "Admission", "Entrée programmée — bilan douleur thoracique", "Douleur thoracique d'effort depuis 3 semaines.", "UF Cardiologie"),
                    ("pe2", "2023-11-11", "09:00", "Acte", "Coronarographie diagnostique", "Sténose serrée de l'IVA proximale, pose d'un stent actif.", "UF Cardiologie interventionnelle"),
                    ("pe3", "2023-11-13", "10:00", "Sortie", "Retour à domicile", "Sortie sous double antiagrégation plaquettaire.", "UF Cardiologie"),
                ],
                "documents": [
                    ("doc1", "2023-11-11", "Compte-rendu d'examen", "CR Coronarographie", "UF Cardiologie interventionnelle",
                     "Sténose serrée de l'artère interventriculaire antérieure proximale, traitée par angioplastie et pose d'un stent actif.",
                     "Sténose serrée de l'artère interventriculaire antérieure proximale, traitée par angioplastie et pose d'un stent actif. Angioplastie réalisée avec succès par voie radiale droite, sans complication au point de ponction. Double antiagrégation plaquettaire instaurée pour une durée de 12 mois."),
                ],
                "constantes": [
                    ("10/11", 78, "142/88", "97%", "36.8°C", "71 kg"),
                    ("13/11", 70, "128/80", "98%", "36.6°C", "71 kg"),
                ],
                "biologie": [
                    ("10/11", "210 ng/L", "78 µmol/L", "80 mL/min", "4 mg/L", "4.2 mmol/L", "13.1 g/dL", "6.8 G/L", "140 mmol/L", "5.4 mmol/L"),
                ],
                "medicaments": [
                    ("Aspirine", 75, "mg", "1x/jour", "2023-11-11", None),
                    ("Clopidogrel", 75, "mg", "1x/jour", "2023-11-11", "2024-11-11"),
                ],
                "codes_valides": [
                    ("v1", "I25.1", "CIM-10", "Maladie coronarienne athéroscléreuse", "2023-11-11", False),
                ],
                "suggestions": [
                    ("s1", "DDAF004", "CCAM", "Angioplastie coronaire avec pose d'endoprothèse", 89, "document", "doc1",
                     "Pose d'un stent actif mentionnée dans le compte-rendu de coronarographie.", "RG-09",
                     "stent actif"),
                ],
            },
        },
        # Documents/observations "hors séjour" : rattachés au patient, pas à
        # un séjour précis — affichés dans un encart fixe de l'onglet Documents.
        "hors_sejour": {
            "documents": [
                ("hdoc1", "2022-09-14", "Courrier de médecin traitant", "Courrier d'adressage en cardiologie", "UF Médecine générale",
                 "Patiente adressée pour bilan de dyspnée d'effort évoluant depuis plusieurs mois, dans un contexte de cardiopathie ischémique connue.",
                 "Patiente adressée pour bilan de dyspnée d'effort évoluant depuis plusieurs mois, dans un contexte de cardiopathie ischémique connue.\nAntécédents : hypertension artérielle, dyslipidémie.\nTraitement actuel : bêta-bloquant, statine.\nMerci de votre avis spécialisé."),
            ],
            "observations": [
                ("hobs1", "2022-09-20", "UF Cardiologie", "Consultation",
                 "Consultation de suivi ambulatoire, patiente stable, pas de décompensation depuis la dernière hospitalisation."),
            ],
        },
    },

    "REC-2024-00099": {
        "sexe": "F", "age": 52,
        "sejour_order": ["sej1", "sej0"],
        "sejours": {
            "sej1": {
                "id_sejour": "ID0000201", "service": "Pneumologie",
                "entree": "2024-04-10", "sortie": "2024-04-16",
                "parcours": [
                    ("pe1", "2024-04-10", "20:10", "Admission", "Entrée via urgences", "Fièvre à 39.2°C, toux productive, douleur basithoracique droite.", "UF Urgences"),
                    ("pe2", "2024-04-10", "21:00", "Acte", "Radiographie thoracique", "Recherche d'un foyer infectieux.", "UF Imagerie"),
                    ("pe3", "2024-04-11", "08:00", "Acte", "Antibiothérapie IV initiée", "Amoxicilline-acide clavulanique.", "UF Pneumologie"),
                    ("pe4", "2024-04-14", "09:30", "Consultation", "Réévaluation clinique", "Apyrexie depuis 48h, amélioration respiratoire.", "UF Pneumologie"),
                    ("pe5", "2024-04-16", "10:00", "Sortie", "Retour à domicile", "Relais par antibiothérapie orale.", "UF Pneumologie"),
                ],
                "documents": [
                    ("doc1", "2024-04-16", "Compte-rendu d'hospitalisation", "CRH — Séjour Pneumologie", "UF Pneumologie",
                     "Pneumopathie basale droite d'allure bactérienne, syndrome inflammatoire biologique marqué à l'entrée. Évolution favorable sous antibiothérapie.",
                     "Pneumopathie basale droite d'allure bactérienne, syndrome inflammatoire biologique marqué à l'entrée. Évolution favorable sous antibiothérapie. Hémocultures négatives, antigénurie légionelle et pneumocoque négatives. Antibiothérapie probabiliste par amoxicilline-acide clavulanique avec relais oral à J5, bonne évolution clinique et biologique."),
                    ("doc2", "2024-04-10", "Compte-rendu de radiologie", "Radiographie thoracique", "UF Imagerie",
                     "Foyer de condensation alvéolaire du lobe inférieur droit, sans épanchement pleural associé.",
                     "Foyer de condensation alvéolaire du lobe inférieur droit, sans épanchement pleural associé. Contrôle radiologique de sortie non réalisé, à prévoir à distance si persistance de symptômes."),
                ],
                "fiches": [
                    ("f1", "Fiche de surveillance respiratoire", "Surveillance", "2024-04-14", "UF Pneumologie", [
                        ("Fréquence respiratoire", "18/min, régulière"),
                        ("Oxygénothérapie", "Sevrage réalisé le 13/04"),
                        ("Toux", "Productive, expectorations en diminution"),
                    ]),
                ],
                "observations": [
                    ("o1", "2024-04-10", "UF Pneumologie", "Clinique",
                     "Fièvre à 39.2°C, toux productive, douleur basithoracique droite à l'admission."),
                    ("o2", "2024-04-14", "UF Pneumologie", "Fonctionnelle",
                     "Apyrexie depuis 48h, amélioration de la toux, reprise d'une activité normale."),
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
                    ("Amoxicilline / Ac. clavulanique", 1, "g", "3x/jour", "2024-04-11", "2024-04-16"),
                ],
                "codes_valides": [
                    ("v1", "J15.9", "CIM-10", "Pneumopathie bactérienne, sans précision", "2024-04-16", False),
                ],
                "suggestions": [
                    ("s1", "J18.1", "CIM-10", "Pneumopathie lobaire, sans précision", 80, "document", "doc2",
                     "Foyer de condensation alvéolaire lobaire décrit sur la radiographie thoracique.", "RG-09",
                     "Foyer de condensation alvéolaire"),
                    ("s2", "R05", "CIM-10", "Toux", 50, "fiche", "f1",
                     "Toux productive en diminution mentionnée dans la fiche de surveillance respiratoire.", "RG-10",
                     "expectorations en diminution"),
                ],
            },
            "sej0": {
                "id_sejour": "ID0000077", "service": "Pneumologie",
                "entree": "2023-03-05", "sortie": "2023-03-09",
                "parcours": [
                    ("pe1", "2023-03-05", "18:40", "Admission", "Entrée via urgences", "Fièvre et toux productive depuis 2 jours.", "UF Urgences"),
                    ("pe2", "2023-03-06", "08:30", "Acte", "Radiographie thoracique", "Foyer basal gauche.", "UF Imagerie"),
                    ("pe3", "2023-03-09", "10:00", "Sortie", "Retour à domicile", "Relais antibiothérapie orale.", "UF Pneumologie"),
                ],
                "documents": [
                    ("doc1", "2023-03-09", "Compte-rendu d'hospitalisation", "CRH — Séjour Pneumologie (2023)", "UF Pneumologie",
                     "Pneumopathie basale gauche, évolution favorable sous antibiothérapie orale.",
                     "Pneumopathie basale gauche, évolution favorable sous antibiothérapie orale. Évolution rapidement favorable sous antibiothérapie orale d'emblée, sans nécessité d'oxygénothérapie."),
                ],
                "constantes": [
                    ("05/03", 98, "112/70", "94%", "38.6°C", "62 kg"),
                ],
                "biologie": [
                    ("05/03", "85 ng/L", "66 µmol/L", "92 mL/min", "96 mg/L", "3.9 mmol/L", "12.9 g/dL", "12.1 G/L", "137 mmol/L", "5.6 mmol/L"),
                ],
                "medicaments": [
                    ("Amoxicilline", 1, "g", "3x/jour", "2023-03-05", "2023-03-12"),
                ],
                "codes_valides": [
                    ("v1", "J18.9", "CIM-10", "Pneumopathie, sans précision", "2023-03-09", False),
                ],
                "suggestions": [],
            },
        },
        "hors_sejour": {
            "fiches": [
                ("hf1", "Fiche de coordination ville-hôpital", "Coordination", "2024-01-15", "UF Pneumologie", [
                    ("Médecin traitant", "Dr Martin, cabinet de Belleville"),
                    ("Pathologie de fond", "BPCO stade II"),
                ]),
            ],
        },
    },

    "REC-2024-00234": {
        "sexe": "M", "age": 74,
        "sejour_order": ["sej1", "sej0"],
        "sejours": {
            "sej1": {
                "id_sejour": "ID0000156", "service": "Chirurgie orthopédique",
                "entree": "2024-06-01", "sortie": "2024-06-07",
                "parcours": [
                    ("pe1", "2024-06-01", "07:30", "Admission", "Entrée en hospitalisation programmée", "Admission la veille de l'intervention, à jeun.", "UF Chirurgie orthopédique"),
                    ("pe2", "2024-06-01", "10:00", "Acte", "Pose de prothèse totale de hanche", "Voie d'abord postéro-externe, sans complication peropératoire.", "UF Bloc opératoire"),
                    ("pe3", "2024-06-02", "09:00", "Consultation", "Visite post-opératoire J1", "Douleur contrôlée, début de la rééducation.", "UF Chirurgie orthopédique"),
                    ("pe4", "2024-06-04", "14:00", "Acte", "Séance de kinésithérapie", "Reprise de l'appui partiel.", "UF Rééducation"),
                    ("pe5", "2024-06-07", "11:00", "Sortie", "Sortie vers centre de rééducation", "Transfert en SSR pour poursuite de la rééducation.", "UF Chirurgie orthopédique"),
                ],
                "documents": [
                    ("doc1", "2024-06-01", "Compte-rendu opératoire", "CR Opératoire — PTH droite", "UF Bloc opératoire",
                     "Mise en place d'une prothèse totale de hanche non cimentée, voie postéro-externe, sans incident peropératoire. Pertes sanguines estimées à 250mL.",
                     "Mise en place d'une prothèse totale de hanche non cimentée, voie postéro-externe, sans incident peropératoire. Pertes sanguines estimées à 250mL. Intervention réalisée sous rachianesthésie, durée opératoire de 55 minutes. Aucune transfusion peropératoire nécessaire. Suites immédiates simples."),
                    ("doc2", "2024-06-07", "Compte-rendu de sortie", "Lettre de sortie", "UF Chirurgie orthopédique",
                     "Patient sortant avec appui partiel, traitement antalgique et anticoagulant préventif pendant 35 jours.",
                     "Patient sortant avec appui partiel, traitement antalgique et anticoagulant préventif pendant 35 jours. Consignes de rééducation transmises au centre de SSR, avec limitation de la flexion de hanche au-delà de 90° pendant 6 semaines."),
                ],
                "fiches": [
                    ("f1", "Fiche de suivi rééducation", "Rééducation", "2024-06-04", "UF Rééducation", [
                        ("Appui", "Partiel, avec cannes anglaises"),
                        ("Amplitude articulaire hanche", "Flexion 70°, pas de limitation en rotation"),
                        ("Douleur (EVA)", "3/10 au repos, 5/10 à la mobilisation"),
                    ]),
                ],
                "observations": [
                    ("o1", "2024-06-02", "UF Chirurgie orthopédique", "Clinique",
                     "Douleur post-opératoire bien contrôlée, cicatrice propre et sèche, pas de signe inflammatoire."),
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
                    ("Rivaroxaban", 10, "mg", "1x/jour", "2024-06-01", None),
                    ("Paracétamol", 1, "g", "4x/jour", "2024-06-01", "2024-06-07"),
                ],
                "codes_valides": [
                    ("v1", "NEQK002", "CCAM", "Arthroplastie totale de hanche par voie postéro-externe", "2024-06-01", False),
                ],
                "suggestions": [
                    ("s1", "Z96.6", "CIM-10", "Présence d'implant articulaire", 88, "document", "doc1",
                     "Pose d'une prothèse totale de hanche mentionnée dans le compte-rendu opératoire.", "RG-09",
                     "prothèse totale de hanche"),
                    ("s2", "M16.1", "CIM-10", "Coxarthrose primaire, autre", 66, "parcours", "pe1",
                     "Hospitalisation programmée pour pose de prothèse de hanche, suggérant une coxarthrose sous-jacente.", "RG-09", None),
                    ("s3", "R52", "CIM-10", "Douleur, non classée ailleurs", 58, "observation", "o1",
                     "Douleur post-opératoire mentionnée dans l'observation clinique du 02/06.", "RG-11",
                     "Douleur post-opératoire"),
                ],
            },
            "sej0": {
                "id_sejour": "ID0000142", "service": "Chirurgie orthopédique",
                "entree": "2024-05-15", "sortie": "2024-05-15",
                "parcours": [
                    ("pe1", "2024-05-15", "09:00", "Consultation", "Consultation chirurgicale", "Indication opératoire retenue, bilan pré-anesthésique programmé.", "UF Chirurgie orthopédique"),
                    ("pe2", "2024-05-15", "10:30", "Acte", "Radiographie du bassin", "Coxarthrose sévère droite confirmée.", "UF Imagerie"),
                ],
                "documents": [
                    ("doc1", "2024-05-15", "Compte-rendu de consultation", "CR Consultation pré-opératoire", "UF Chirurgie orthopédique",
                     "Coxarthrose évoluée symptomatique, indication de prothèse totale de hanche retenue.",
                     "Coxarthrose évoluée symptomatique, indication de prothèse totale de hanche retenue. Bilan pré-anesthésique programmé, absence de contre-indication à l'intervention à ce stade."),
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
                     "Coxarthrose évoluée symptomatique mentionnée dans le compte-rendu de consultation.", "RG-09",
                     "Coxarthrose évoluée symptomatique"),
                ],
            },
        },
    },
}


DOSE_HOURS_BY_FREQUENCY = {
    1: ["08:00"],
    2: ["08:00", "20:00"],
    3: ["08:00", "14:00", "20:00"],
    4: ["08:00", "12:00", "16:00", "20:00"],
}


def _dose_hours(frequence):
    """Déduit les heures de prise quotidiennes à partir d'une fréquence du type "2x/jour"."""
    m = re.match(r"(\d+)x/jour", frequence)
    n = int(m.group(1)) if m else 1
    return DOSE_HOURS_BY_FREQUENCY.get(n, ["08:00"])


def _clamp(d, lo, hi):
    return max(lo, min(d, hi))


def _daterange(start, end):
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    days = []
    d = d0
    while d <= d1:
        days.append(d.isoformat())
        d += timedelta(days=1)
    return days


def _generate_medicament_rows(patient_id, id_sejour, nom, qte, unite, frequence, debut, fin,
                               sejour_entree, sejour_sortie):
    """Génère une ligne par prise effective d'un médicament (date_administration
    complète), bornées à la durée du séjour."""
    atc, ucd = ATC_UCD_BY_DRUG[nom]
    start = _clamp(debut, sejour_entree, sejour_sortie)
    end = _clamp(fin or sejour_sortie, sejour_entree, sejour_sortie)
    if end < start:
        return []
    rows = []
    for day in _daterange(start, end):
        for heure in _dose_hours(frequence):
            rows.append({
                "patient_id": patient_id, "id_sejour": id_sejour, "nom": nom,
                "qte": qte, "unite": unite, "atc": atc, "ucd": ucd,
                "date_administration": f"{day} {heure}",
            })
    return rows


def _split_valeur_unite(raw):
    """Sépare une valeur de biologie du prototype (ex: "5400 ng/L") en un
    nombre et une unité, pour coller au format long (code/valeur/unite)."""
    m = re.match(r"([\d.]+)\s*(.*)", raw)
    if not m:
        return raw, ""
    nombre = m.group(1)
    valeur = float(nombre) if "." in nombre else int(nombre)
    return valeur, m.group(2)


def build_tables():
    patients_rows, sejours_rows = [], []
    parcours_rows, documents_rows = [], []
    fiches_rows, observations_rows = [], []
    constantes_rows, biologie_rows = [], []
    medicaments_rows = []
    codes_valides_rows, suggestions_rows = [], []

    for patient_id, p in PATIENTS.items():
        patients_rows.append({"patient_id": patient_id, "sexe": p["sexe"], "age": p["age"]})

        for ordre, sejour_key in enumerate(p["sejour_order"]):
            s = p["sejours"][sejour_key]
            id_sej = s["id_sejour"]
            sejours_rows.append({
                "patient_id": patient_id, "ordre": ordre, "id_sejour": id_sej,
                "service": s["service"], "entree": s["entree"], "sortie": s["sortie"],
            })

            for (eid, date_, heure, typ, titre, detail, uf) in s["parcours"]:
                parcours_rows.append({
                    "patient_id": patient_id, "id_sejour": id_sej, "event_id": eid,
                    "date": date_, "heure": heure, "type": typ, "titre": titre,
                    "detail": detail, "uf": uf,
                })

            for (did, date_, typ, titre, uf, excerpt, full_text) in s["documents"]:
                documents_rows.append({
                    "patient_id": patient_id, "id_sejour": id_sej, "doc_id": did,
                    "date": date_, "type": typ, "titre": titre, "uf": uf,
                    "excerpt": excerpt, "full_text": full_text,
                })

            for (fid, titre, typ, date_, uf, champs) in s.get("fiches", []):
                for ordre_champ, (label, valeur) in enumerate(champs):
                    fiches_rows.append({
                        "patient_id": patient_id, "id_sejour": id_sej, "fiche_id": fid,
                        "titre": titre, "type": typ, "date": date_, "uf": uf,
                        "champ_ordre": ordre_champ, "champ_label": label, "champ_valeur": valeur,
                    })

            for (oid, date_, uf, categorie, texte) in s.get("observations", []):
                observations_rows.append({
                    "patient_id": patient_id, "id_sejour": id_sej, "observation_id": oid,
                    "date": date_, "uf": uf, "categorie": categorie, "texte": texte,
                })

            for (date_, fc, ta, spo2, temp, poids) in s["constantes"]:
                constantes_rows.append({
                    "patient_id": patient_id, "id_sejour": id_sej, "date": date_,
                    "fc": fc, "ta": ta, "spo2": spo2, "temp": temp, "poids": poids,
                })

            for (date_, *valeurs) in s["biologie"]:
                for code, raw in zip(BIOLOGIE_CODES, valeurs):
                    valeur, unite = _split_valeur_unite(raw)
                    biologie_rows.append({
                        "patient_id": patient_id, "id_sejour": id_sej, "date": date_,
                        "code": code, "valeur": valeur, "unite": unite,
                    })

            for (nom, qte, unite, freq, debut, fin) in s["medicaments"]:
                medicaments_rows.extend(_generate_medicament_rows(
                    patient_id, id_sej, nom, qte, unite, freq, debut, fin, s["entree"], s["sortie"]))

            for (cid, code, typ, libelle, date_, removed) in s["codes_valides"]:
                codes_valides_rows.append({
                    "patient_id": patient_id, "id_sejour": id_sej, "code_id": cid,
                    "code": code, "type": typ, "libelle": libelle,
                    "date": date_, "removed": removed,
                })

            for (sid, code, typ, libelle, confiance, src_kind, src_id, justification, regle_id, highlight) in s["suggestions"]:
                suggestions_rows.append({
                    "patient_id": patient_id, "id_sejour": id_sej, "suggestion_id": sid,
                    "code": code, "type": typ, "libelle": libelle, "confiance": confiance,
                    "source_kind": src_kind, "source_id": src_id, "justification": justification,
                    "regle_id": regle_id, "highlight": highlight,
                })

        # Documents/fiches/observations hors séjour : id_sejour laissé vide.
        hs = p.get("hors_sejour", {})
        for (did, date_, typ, titre, uf, excerpt, full_text) in hs.get("documents", []):
            documents_rows.append({
                "patient_id": patient_id, "id_sejour": None, "doc_id": did,
                "date": date_, "type": typ, "titre": titre, "uf": uf,
                "excerpt": excerpt, "full_text": full_text,
            })
        for (fid, titre, typ, date_, uf, champs) in hs.get("fiches", []):
            for ordre_champ, (label, valeur) in enumerate(champs):
                fiches_rows.append({
                    "patient_id": patient_id, "id_sejour": None, "fiche_id": fid,
                    "titre": titre, "type": typ, "date": date_, "uf": uf,
                    "champ_ordre": ordre_champ, "champ_label": label, "champ_valeur": valeur,
                })
        for (oid, date_, uf, categorie, texte) in hs.get("observations", []):
            observations_rows.append({
                "patient_id": patient_id, "id_sejour": None, "observation_id": oid,
                "date": date_, "uf": uf, "categorie": categorie, "texte": texte,
            })

    return {
        "patients": pd.DataFrame(patients_rows),
        "sejours": pd.DataFrame(sejours_rows),
        "parcours": pd.DataFrame(parcours_rows),
        "documents": pd.DataFrame(documents_rows),
        "fiches": pd.DataFrame(fiches_rows),
        "observations": pd.DataFrame(observations_rows),
        "constantes": pd.DataFrame(constantes_rows),
        "biologie": pd.DataFrame(biologie_rows),
        "medicaments": pd.DataFrame(medicaments_rows),
        "codes_valides": pd.DataFrame(codes_valides_rows),
        "suggestions": pd.DataFrame(suggestions_rows),
    }


if __name__ == "__main__":
    tables = build_tables()
    for name, df in tables.items():
        path = DATA_DIR / f"{name}.xlsx"
        df.to_excel(path, index=False)
        print(f"  {name:15s} -> {path}  ({len(df)} lignes)")
    print("\nDonnées de référence générées dans", DATA_DIR)
