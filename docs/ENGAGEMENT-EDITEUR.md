# Engagement de l'éditeur du logiciel (projet)

> **Projet, non officiel.** Rédigé en octobre 2026 à partir de l'article 9 du
> décret exécutif n° 09-110 et des articles 20 ter et 51 sexies du code des
> procédures fiscales (loi de finances pour 2026). Le modèle d'engagement est
> renvoyé à un arrêté du ministre des finances non publié à cette date : ce
> texte sera revu dès sa publication. Il ne décrit que ce que le logiciel fait
> réellement (voir COMPLIANCE.md) ; ne le signez jamais pour une fonction qui
> n'existe pas.

---

**[Raison sociale de l'éditeur]**, [forme juridique], [adresse],
RC n° [...], NIF [...], NIS [...], représenté par [nom, qualité],
ci-après « l'éditeur »,

s'engage envers **[raison sociale du client]**, NIF [...], ci-après « le
client », pour le logiciel :

- **Nom** : Daftar, fondé sur ERPNext (logiciel libre, Frappe Technologies),
  avec les applications Daftar dz_core [et dz_cod] ;
- **Version** : dz_core [0.4.0] [, dz_cod 0.4.0], ERPNext et Frappe [16.x] ;
- **Modules couverts** : comptabilité générale, ventes et facturation, achats,
  stocks [, fabrication] [, vente en ligne contre remboursement] ;
- **Mis en service le** : [date], sur le serveur [hébergeur, lieu].

## 1. Conformité

L'éditeur déclare que, dans la version et le paramétrage livrés au client, le
logiciel :

1. interdit toute modification ou suppression d'une écriture validée :
   l'annulation d'un document passe une écriture de contrepassation datée du
   jour de l'annulation et conserve l'écriture d'origine ; aucun utilisateur
   n'a le droit de supprimer une pièce comptable ou de stock, même en
   brouillon, ni de supprimer les transactions d'une société ;
2. numérote les pièces dans des séries chronologiques continues, une série
   par type de pièce et par année, sans trou puisque aucune pièce ne peut être
   supprimée (une pièce annulée garde son numéro) ;
3. rattache chaque écriture à un journal (ventes, achats, caisse, banque,
   stocks, opérations diverses, à-nouveaux) et produit le journal
   centralisateur mensuel ;
4. reporte automatiquement les soldes des comptes de bilan d'un exercice à
   l'autre ;
5. permet de geler chaque mois et chaque exercice clos, après quoi aucune
   écriture n'est possible à une date antérieure, sauf pour le rôle que les
   paramètres comptables y autorisent [aucun / préciser] ;
6. conserve, pour chaque validation, annulation ou modification après
   validation, l'utilisateur, la date, l'heure, l'adresse IP et le poste
   (navigateur) ;
7. produit, sur demande, le fichier des écritures d'une période (format texte
   et tableur), avec son empreinte SHA-256 ;
8. produit chaque année une archive de l'exercice gelé (écritures, livres,
   états financiers, journal d'audit), chaque fichier avec son empreinte
   SHA-256, conservée dix ans sur le serveur et sauvegardée chaque jour hors
   du serveur ;
9. imprime des factures portant les mentions du décret exécutif n° 05-468 et
   la mention « facture annulée » sur une facture annulée.

## 2. Engagement de communication

L'éditeur s'engage à remettre à l'administration fiscale, à sa demande, les
codes sources des applications Daftar, les données, les traitements et la
documentation du logiciel, dans la version utilisée par le client
(article 51 sexies du code des procédures fiscales). Les codes sources
d'ERPNext et de Frappe sont publics.

## 3. Limites

- [Lister ici ce qui n'est pas encore fourni à la date de signature, par
  exemple : certification par un organisme habilité (aucun organisme connu à
  ce jour), format officiel du fichier des écritures (arrêté non publié).]
- Le client reste responsable de l'usage du logiciel : un utilisateur par
  personne, contrôles et gel mensuels, conservation des pièces justificatives
  papier.

## 4. Durée

Cet engagement vaut pour la version désignée ci-dessus et pour chaque mise à
jour livrée par l'éditeur, qui en informe le client par écrit.

Fait à [ville], le [date].

| Pour l'éditeur | Pour le client |
| --- | --- |
| [nom, qualité, signature, cachet] | [nom, qualité, signature, cachet] |
