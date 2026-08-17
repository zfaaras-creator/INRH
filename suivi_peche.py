"""
APP SIMPLE : Tu donnes le dossier UNE SEULE FOIS,
puis tu poses tes questions directement (en langage normal).
============================================================
Version originale — base de données locale (SQLite).
Aucune donnée ne quitte ton ordinateur.

Exemple d'utilisation :
    Dossier : mes_fichiers
    Ta question : poids du lundi à Boujdour
    Ta question : jeudi toutes les villes
    Ta question : quitter
"""

import os
import sqlite3
import pandas as pd

NOM_BASE = "ma_base.db"
NOM_TABLE = "activite_peche"

JOURS = {
    0: "lundi", 1: "mardi", 2: "mercredi", 3: "jeudi",
    4: "vendredi", 5: "samedi", 6: "dimanche",
}


def trouver_ligne_entete(tableau):
    for numero_ligne in range(len(tableau)):
        ligne = tableau.iloc[numero_ligne]
        for valeur in ligne:
            if valeur == "DATE_EXPLOITATION":
                return numero_ligne
    return None


def trouver_nom_ville(tableau):
    for numero_ligne in range(len(tableau)):
        ligne = tableau.iloc[numero_ligne]
        for valeur in ligne:
            if isinstance(valeur, str) and "CAPI" in valeur.upper():
                return valeur.upper().replace("CAPI", "").strip().title()
    return "Ville inconnue"


def importer_fichier(chemin_fichier):
    tableau_brut = pd.read_excel(chemin_fichier, header=None)
    ligne_entete = trouver_ligne_entete(tableau_brut)
    if ligne_entete is None:
        print(f"  ❌ Format non reconnu : {os.path.basename(chemin_fichier)}")
        return

    ville = trouver_nom_ville(tableau_brut)

    donnees = pd.read_excel(chemin_fichier, header=ligne_entete)
    donnees = donnees.dropna(how="all")

    colonnes_utiles = [
        "DATE_EXPLOITATION", "NOM_BATEAU", "CODE_BATEAU",
        "CAT_ESPECE", "Poids_total", "DESIG_DESTINATION",
    ]
    colonnes_presentes = [c for c in colonnes_utiles if c in donnees.columns]
    donnees = donnees[colonnes_presentes]
    donnees = donnees.rename(columns={"DATE_EXPLOITATION": "date"})
    donnees["date"] = pd.to_datetime(donnees["date"], dayfirst=True, errors="coerce")
    donnees["ville"] = ville
    donnees["jour"] = donnees["date"].dt.dayofweek.map(JOURS)

    connexion = sqlite3.connect(NOM_BASE)
    try:
        anciennes_donnees = pd.read_sql(f"SELECT * FROM {NOM_TABLE}", connexion)
        anciennes_donnees["date"] = pd.to_datetime(anciennes_donnees["date"], errors="coerce")
        donnees = pd.concat([anciennes_donnees, donnees], ignore_index=True)
        donnees = donnees.drop_duplicates()
    except Exception:
        pass

    donnees.to_sql(NOM_TABLE, connexion, if_exists="replace", index=False)
    connexion.close()

    print(f"  ✅ {os.path.basename(chemin_fichier)} -> ville : {ville} ({len(donnees)} lignes au total en base)")


def importer_dossier(dossier):
    if not os.path.isdir(dossier):
        print("❌ Ce dossier n'existe pas.")
        return False

    fichiers = [f for f in os.listdir(dossier) if f.endswith(".xlsx")]
    if not fichiers:
        print("⚠️  Aucun fichier .xlsx trouvé dans ce dossier.")
        return False

    print(f"\n📥 Import de {len(fichiers)} fichier(s)...")
    for nom_fichier in fichiers:
        importer_fichier(os.path.join(dossier, nom_fichier))
    print("✅ Import terminé !\n")
    return True


def lire_toutes_les_donnees():
    connexion = sqlite3.connect(NOM_BASE)
    donnees = pd.read_sql(f"SELECT * FROM {NOM_TABLE}", connexion)
    donnees["date"] = pd.to_datetime(donnees["date"], errors="coerce")
    connexion.close()
    return donnees


MOTS_COLONNES = {
    "poids": "Poids_total",
    "kilo": "Poids_total",
    "kg": "Poids_total",
    "bateau": "NOM_BATEAU",
    "code": "CODE_BATEAU",
    "espece": "CAT_ESPECE",
    "espèce": "CAT_ESPECE",
    "destination": "DESIG_DESTINATION",
}


def sans_accent(texte):
    texte = texte.lower()
    remplacements = {
        "â": "a", "à": "a", "ä": "a",
        "ê": "e", "è": "e", "é": "e", "ë": "e",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "û": "u", "ù": "u", "ü": "u",
        "ç": "c",
    }
    for lettre_accentuee, lettre_simple in remplacements.items():
        texte = texte.replace(lettre_accentuee, lettre_simple)
    return texte


def repondre_a_la_question(question):
    donnees = lire_toutes_les_donnees()
    question_minuscule = sans_accent(question)

    jour_trouve = None
    for jour in JOURS.values():
        if jour in question_minuscule:
            jour_trouve = jour
            break

    villes_disponibles = donnees["ville"].dropna().unique()
    ville_trouvee = None
    for ville in villes_disponibles:
        if sans_accent(ville) in question_minuscule:
            ville_trouvee = ville
            break

    colonnes_demandees = []
    for mot_cle, nom_colonne in MOTS_COLONNES.items():
        if mot_cle in question_minuscule and nom_colonne not in colonnes_demandees:
            colonnes_demandees.append(nom_colonne)

    resultat = donnees
    if jour_trouve:
        resultat = resultat[resultat["jour"] == jour_trouve]
    if ville_trouvee:
        resultat = resultat[resultat["ville"] == ville_trouvee]

    if resultat.empty:
        print("⚠️  Je n'ai pas trouvé de résultat pour cette question.")
        print("    Essaie par exemple : 'poids du lundi à Boujdour'")
        return

    resultat = resultat.copy()
    if colonnes_demandees:
        colonnes_a_afficher = ["date", "ville"] + colonnes_demandees
    else:
        colonnes_a_afficher = list(resultat.columns)

    resultat["date"] = resultat["date"].dt.strftime("%d-%m-%Y")
    resultat = resultat[colonnes_a_afficher]

    print(f"\n📋 Résultat ({len(resultat)} lignes) :\n")
    print(resultat.to_string(index=False))
    print()


def main():
    print("=" * 55)
    print(" APP DE SUIVI DE PÊCHE — base de données locale")
    print("=" * 55)

    dossier = input("\n📁 Donne le chemin du dossier avec tes fichiers : ").strip()
    ok = importer_dossier(dossier)
    if not ok:
        return

    print("Tu peux maintenant poser tes questions directement.")
    print("Exemple : 'poids du lundi à Boujdour'")
    print("Tape 'quitter' pour arrêter.\n")

    while True:
        question = input("❓ Ta question : ").strip()

        if question.lower() in ("quitter", "stop", "exit"):
            print("👋 Au revoir !")
            break

        repondre_a_la_question(question)


if __name__ == "__main__":
    main()
