Version : Final V3

Langage : Python 3.x

1. Vue d'ensemble
Ce projet est une implémentation graphique du jeu de Poker (variante simplifiée "5-card draw"). Il permet à un utilisateur de jouer seul contre une IA ("Luigi") ou contre un autre joueur humain via un réseau local (LAN). L'application gère la persistance des crédits (économie du jeu), les effets sonores et une interface utilisateur moderne.



2. Stack Technique et Librairies
Le projet repose sur plusieurs bibliothèques standard et externes pour gérer les différents aspects du jeu :

Interface Graphique (GUI) : tkinter (et ttk) pour la gestion des fenêtres et des widgets. Utilisation de Canvas pour dessiner des composants personnalisés (boutons arrondis).

Multimédia :

PIL (Pillow) : Manipulation et affichage des images (cartes, dos de cartes) avec gestion de la transparence (Alpha channel).

pygame.mixer : Gestion du moteur audio (musique de fond et bruitages SFX) pour une exécution fluide sans bloquer l'interface.

Réseau : socket (TCP/IP) pour la communication, threading pour l'écoute asynchrone, et pickle pour la sérialisation des objets Python.

Données : json pour la sauvegarde locale du solde des joueurs.

3. Architecture Logicielle
Le code est structuré selon une approche Orientée Objet (POO) pour garantir la maintenabilité et la séparation des responsabilités.

A. Classes Métier (Logique du Poker)
Carte : Représente une carte avec une valeur (7 à As) et une couleur.

JeuDeCartes : Gère le paquet de 32 cartes, le mélange (random.shuffle) et la distribution (pop).

MainJoueur : Contient les cartes d'un joueur.

Méthode clé : evaluer_main(). Cette méthode analyse la main pour détecter les combinaisons (Paire, Brelan, Carré, Quinte Flush, etc.). Elle retourne un score hiérarchique permettant de comparer deux mains.


B. Gestion Réseau (NetworkManager)
Cette classe encapsule toute la complexité des sockets TCP.

Protocole Robuste : Pour éviter la fragmentation des paquets TCP (problème courant où un message arrive en plusieurs morceaux), j'ai implémenté un protocole de "Length-Prefix Framing".

Chaque message est précédé de 4 octets (struct.pack('>I', len)) indiquant la taille des données.

La méthode _recv_all garantit la réception complète du message avant la désérialisation via pickle.

Architecture Client/Serveur : Le jeu peut agir soit comme Hôte (Bind/Listen), soit comme Client (Connect).

C. Interface Utilisateur (PokerAppModern)
C'est le contrôleur principal de l'application.

Cycle de vie : Initialise le jeu, charge les ressources, et lance la boucle principale mainloop().

Gestion des États : Gère les transitions entre le mode "Solo" et "LAN" (attente de connexion, échange de cartes, révélation).

Design : Utilisation d'une palette de couleurs cohérente ("Dark Mode") et création d'une fonction bouton_arrondi pour un rendu esthétique supérieur aux boutons natifs de Tkinter.

4. Points Techniques Notables
Algorithme d'évaluation des mains
L'évaluation des mains ne se base pas sur de simples conditions if/else, mais sur une analyse statistique des cartes :

Comptage des occurrences de chaque valeur (fréquence).

Tri des combinaisons par force (ex: Carré > Brelan > Paire).

Gestion des égalités (Kicker) : Si deux joueurs ont une "Paire", l'algorithme compare la valeur de la paire, puis les cartes restantes.

Gestion des Ressources (resource_path)
Une fonction utilitaire resource_path a été intégrée pour gérer les chemins de fichiers (images/sons). Elle permet au programme de fonctionner aussi bien en tant que script .py qu'en tant qu'exécutable compilé .exe (via PyInstaller), en détectant le dossier temporaire sys._MEIPASS.

Synchronisation LAN
En mode multijoueur, le jeu utilise un système de messages sérialisés (dictionnaires JSON-like via Pickle) :

START : L'hôte génère le paquet, distribue une main au client et lance la partie.

HAND : Les joueurs envoient leur main finale cryptée (objet sérialisé).

Comparaison locale : Une fois les deux mains reçues, chaque client exécute la comparaison localement pour déterminer le vainqueur.

Solo : Jouer contre l'ordinateur.

Host : Créer une partie sur le réseau local (affiche l'IP à partager).

Client : Rejoindre une partie via l'IP de l'hôte.
