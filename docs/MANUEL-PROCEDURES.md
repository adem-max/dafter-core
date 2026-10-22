# Manuel des procédures comptables (Daftar)

À remettre au client avec ses accès. Ce manuel décrit comment la comptabilité
est tenue dans Daftar et ce que chacun doit faire. Il complète l'engagement de
l'éditeur et sert de documentation au sens de l'article 7 du décret exécutif
n° 09-110.

## 1. Les utilisateurs

- **Un compte par personne**, jamais de compte partagé : chaque opération
  porte le nom de celui qui l'a faite, son adresse IP et son poste.
- Les droits suivent le rôle : gérant, comptabilité, ventes, production,
  stock. Personne ne peut supprimer une pièce comptable ou de stock.
- Un départ : le compte est désactivé le jour même, jamais supprimé.

## 2. Les pièces

- **Chaque vente donne une facture**, y compris chaque colis livré contre
  remboursement. La facture porte les mentions légales.
- **Chaque achat est saisi avec la facture du fournisseur** (numéro et date).
  Un achat sans facture se saisit avec la case « Sans facture (justificatif
  interne) » et un bon d'achat signé du vendeur : il ne donne jamais de TVA
  déductible.
- Les pièces papier sont classées par mois et conservées **dix ans**.

## 3. Corriger une erreur

- Une pièce validée ne se modifie pas. On l'**annule** (Daftar passe une
  contrepassation datée du jour) et on en saisit une nouvelle, ou on passe une
  pièce de correction : avoir, écriture de régularisation.
- Après le gel d'un mois, toute correction se fait dans le mois ouvert.

## 4. Chaque mois

Rapport **Clôture du mois**, dans l'ordre :

1. les comptes d'attente à zéro : 6589 (charges à reclasser), 4781
   (versements à identifier), 476, 479 (ouverture) ;
2. le 4081 : reclasser les soldes débiteurs au 4097 (bouton) ;
3. la production : classe 72 égale à la variation des stocks de produits ;
4. vente en ligne : le compte de chaque transporteur égal aux colis livrés
   non encore versés, et ses factures saisies ;
5. les déclarations du mois : G50 avant le 20 (régime réel), G12
   prévisionnel avant le 30 juin, G12 bis avant le 20 janvier (IFU,
   auto-entrepreneur) ;
6. **Geler le mois**.

Régime réel : rapport **Aide G50**, écriture de liquidation de la TVA,
droit de timbre du mois, TVA à reverser sur les pertes, vols et dons.
IFU et auto-entrepreneur : **Registre des ventes** (des recettes) et
**Registre des achats** à recopier dans les registres côtés et paraphés.

## 5. Chaque année

Rapport **Exercice comptable** :

1. les contrôles de fin d'année au vert ;
2. **Clôturer l'exercice** (le résultat passe au 120 ou au 129) ;
3. **Geler l'exercice** ;
4. **Dossier de clôture** : à remettre au comptable (Excel, PDF et fichier
   des écritures) ;
5. **Archive annuelle** : conservée dix ans, avec l'empreinte de chaque
   fichier.

Après la décision des associés ou de l'exploitant, le comptable affecte le
résultat par une écriture.

## 6. Sauvegardes

Le serveur est sauvegardé chaque nuit hors du serveur ; une restauration est
testée régulièrement. En cas de panne, l'éditeur restaure la dernière
sauvegarde et le client ressaisit les pièces de la journée.
