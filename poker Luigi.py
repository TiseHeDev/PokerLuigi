import tkinter as tk
from tkinter import messagebox
import random
import json
import os
from PIL import Image, ImageTk, ImageDraw
import pygame

# ==========================================
# Chemins absolus
# ==========================================
dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_images = os.path.join(dossier_script, "images")
dossier_sons = os.path.join(dossier_script, "sons")
FICHIER_SOLDE = os.path.join(dossier_script, "solde.json")

# ==========================================
# Initialisation du son
# ==========================================
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Attention : impossible d'initialiser le son : {e}")

SON_VICTOIRE = os.path.join(dossier_sons, "victoire.wav")
SON_DEFAITE = os.path.join(dossier_sons, "defaite.wav")
SON_EGALITE = os.path.join(dossier_sons, "egalite.wav")
SON_CLAP = os.path.join(dossier_sons, "clap.wav")
SON_FOND = os.path.join(dossier_sons, "fond.mp3")
SON_START = os.path.join(dossier_sons, "start.wav")
SON_DISTRIB = os.path.join(dossier_sons, "card_distrib.wav")

def jouer_son(fichier):
    if not os.path.exists(fichier):
        # print(f"Fichier son introuvable : {fichier}")
        return
    try:
        snd = pygame.mixer.Sound(fichier)
        snd.play()
    except Exception as e:
        print(f"Erreur lecture son : {e}")

def jouer_musique_fond():
    if not os.path.exists(SON_FOND):
        return
    try:
        pygame.mixer.music.load(SON_FOND)
        pygame.mixer.music.set_volume(0.45)
        pygame.mixer.music.play(-1)  # boucle infinie
    except Exception as e:
        print(f"Erreur musique fond : {e}")

# ==========================================
# Sauvegarde des soldes
# ==========================================
def charger_solde():
    if os.path.exists(FICHIER_SOLDE):
        try:
            with open(FICHIER_SOLDE, "r") as f:
                data = json.load(f)
            return data.get("joueur", 100), data.get("luigi", 100)
        except Exception:
            return 100, 100
    else:
        return 100, 100

def sauvegarder_solde(solde_joueur, solde_luigi):
    data = {"joueur": solde_joueur, "luigi": solde_luigi}
    try:
        with open(FICHIER_SOLDE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Impossible de sauvegarder le solde : {e}")

# ==========================================
# Logique du jeu (inchangée)
# ==========================================
class Carte:
    valeurs = ['7', '8', '9', '10', 'Valet', 'Dame', 'Roi', 'As']
    couleurs = ['♥', '♦', '♣', '♠']

    def __init__(self, valeur, couleur):
        self.valeur = valeur
        self.couleur = couleur

    def __repr__(self):
        return f"{self.valeur}{self.couleur}"

    def valeur_num(self):
        return Carte.valeurs.index(self.valeur)

class JeuDeCartes:
    def __init__(self):
        self.cartes = [Carte(v, c) for v in Carte.valeurs for c in Carte.couleurs]
        self.melanger()

    def melanger(self):
        random.shuffle(self.cartes)

    def piocher(self):
        return self.cartes.pop() if self.cartes else None

class MainJoueur:
    def __init__(self):
        self.cartes = []

    def ajouter(self, carte):
        self.cartes.append(carte)

    def evaluer_main(self):
        valeurs = [c.valeur for c in self.cartes]
        couleurs = [c.couleur for c in self.cartes]
        nums = sorted([Carte.valeurs.index(v) for v in valeurs])
        unique_vals = len(set(valeurs))
        flush = len(set(couleurs)) == 1
        straight = all(nums[i] + 1 == nums[i + 1] for i in range(4))

        counts = {v: valeurs.count(v) for v in set(valeurs)}
        tri_counts = sorted(counts.items(), key=lambda x: (x[1], Carte.valeurs.index(x[0])), reverse=True)
        ordre_valeurs = [Carte.valeurs.index(v) for v, _ in tri_counts]

        if flush and straight:
            return (8, "Quinte Flush", ordre_valeurs)
        elif unique_vals == 2:
            if any(valeurs.count(v) == 4 for v in valeurs):
                return (7, "Carré", ordre_valeurs)
            else:
                return (6, "Full", ordre_valeurs)
        elif flush:
            return (5, "Couleur", ordre_valeurs)
        elif straight:
            return (4, "Suite", ordre_valeurs)
        elif any(valeurs.count(v) == 3 for v in valeurs):
            return (3, "Brelan", ordre_valeurs)
        elif sum(1 for v in set(valeurs) if valeurs.count(v) == 2) == 2:
            return (2, "Double Paire", ordre_valeurs)
        elif any(valeurs.count(v) == 2 for v in valeurs):
            return (1, "Paire", ordre_valeurs)
        else:
            return (0, "Carte haute", ordre_valeurs)

class Joueur:
    def __init__(self, nom, solde=100):
        self.nom = nom
        self.solde = solde
        self.main = MainJoueur()

    def miser(self, montant):
        if montant > self.solde:
            return False
        self.solde -= montant
        return True

    def recevoir_gain(self, montant):
        self.solde += montant

class PartiePoker:
    def __init__(self, solde_joueur=100, solde_luigi=100):
        self.jeu = JeuDeCartes()
        self.joueur = Joueur("Toi", solde_joueur)
        self.luigi = Joueur("Luigi", solde_luigi)

    def distribuer(self):
        # Réinitialiser les mains
        self.joueur.main.cartes = []
        self.luigi.main.cartes = []
        # Re-mélanger et distribuer
        self.jeu.melanger()
        for _ in range(5):
            self.joueur.main.ajouter(self.jeu.piocher())
            self.luigi.main.ajouter(self.jeu.piocher())
            # jouer_son(SON_DISTRIB) # Retiré, car trop répétitif, on peut le jouer une seule fois avant la distribution.

    def echanger_cartes(self, indices):
        for i in indices:
            self.joueur.main.cartes[i] = self.jeu.piocher()

    def tour_luigi(self):
        score, type_main, ordre = self.luigi.main.evaluer_main()
        cartes_a_echanger = []
        # Logique de base : Si pas de bonne main, échange les 3 plus faibles
        if score < 4:
            # Récupère les indices des 3 cartes avec la valeur la plus faible
            # Utilise un tri par la valeur numérique de la carte
            indices_tries = sorted(range(5), key=lambda i: self.luigi.main.cartes[i].valeur_num())
            cartes_a_echanger = indices_tries[:3]
            
        for i in cartes_a_echanger:
            self.luigi.main.cartes[i] = self.jeu.piocher()

    def comparer(self, mise):
        s_j, t_j, v_j = self.joueur.main.evaluer_main()
        s_l, t_l, v_l = self.luigi.main.evaluer_main()
        
        # Le joueur doit payer sa mise AVANT de comparer
        if not self.joueur.miser(mise):
             return "Erreur de mise: Solde insuffisant !" # Ne devrait pas arriver avec la logique de mise

        # Comparaison de la force de la main (score)
        if s_j > s_l:
            self.joueur.recevoir_gain(mise * 2)
            jouer_son(SON_VICTOIRE)
            jouer_son(SON_CLAP)
            return f"🎉 Tu gagnes ! ({t_j} contre {t_l})"
        # Si les mains sont égales, comparer la carte haute (v_j et v_l sont des listes ordonnées)
        elif s_j == s_l:
            if v_j > v_l: # Comparaison des listes d'ordres (Python le gère lexicographiquement)
                self.joueur.recevoir_gain(mise * 2)
                jouer_son(SON_VICTOIRE)
                jouer_son(SON_CLAP)
                return f"🎉 Tu gagnes ! ({t_j} contre {t_l} - Carte Haute)"
            elif v_j < v_l:
                self.luigi.recevoir_gain(mise * 2)
                jouer_son(SON_DEFAITE)
                return f"😬 Luigi gagne... ({t_l} contre {t_j} - Carte Haute)"
            else: # Égalité parfaite (même score et mêmes cartes hautes)
                self.joueur.recevoir_gain(mise) # Récupère juste la mise
                self.luigi.solde += mise # Luigi récupère juste sa mise (car les mises sont payées avant la comparaison)
                jouer_son(SON_EGALITE)
                return f"🤝 Égalité parfaite ! ({t_j})"
        # Si le score de Luigi est supérieur
        else:
            self.luigi.recevoir_gain(mise * 2)
            jouer_son(SON_DEFAITE)
            return f"😬 Luigi gagne... ({t_l} contre {t_j})"

# ==========================================
# Bouton arrondi adaptatif (amélioré)
# ==========================================
def bouton_arrondi(parent, texte, command, hauteur=45, couleur="#4CAF50", couleur_hover="#66BB6A", couleur_texte="white", largeur=None):
    if largeur is None:
        largeur = max(180, len(texte)*12)
    
    # Créer le Canvas avec une couleur de fond pour simuler l'ombre
    SHADOW_COLOR = "#222222"
    canvas = tk.Canvas(parent, width=largeur, height=hauteur, bg=parent["bg"], highlightthickness=0)
    
    radius = 12
    x0, y0, x1, y1 = 0, 0, largeur, hauteur
    
    # Dessiner l'ombre (décalage de 2px en bas et à droite)
    shadow_rect = (x0 + 2, y0 + 2, x1, y1)
    canvas.create_arc(x1 - radius * 2, y1 - radius * 2, x1, y1, start=270, extent=90, fill=SHADOW_COLOR, outline=SHADOW_COLOR) # coin bas droit
    canvas.create_arc(x0 + 2, y1 - radius * 2, x0 + 2 + radius * 2, y1, start=180, extent=90, fill=SHADOW_COLOR, outline=SHADOW_COLOR) # coin bas gauche
    canvas.create_rectangle(x0 + 2 + radius, y1 - 2, x1 - radius, y1, fill=SHADOW_COLOR, outline=SHADOW_COLOR, width=0) # bas
    canvas.create_rectangle(x1 - 2, y0 + 2 + radius, x1, y1 - radius, fill=SHADOW_COLOR, outline=SHADOW_COLOR, width=0) # droite
    
    # Dessiner le rectangle principal (pour les coins arrondis, on se simplifie la vie en utilisant des rectangles et des ovales)
    rect_coords = (x0, y0, x1 - 2, y1 - 2) # Légèrement décalé pour voir l'ombre
    rect_id = canvas.create_rectangle(rect_coords, fill=couleur, outline=couleur, width=0)
    
    # Le texte doit être au-dessus
    text_id = canvas.create_text((largeur - 2)/2, (hauteur - 2)/2, text=texte, fill=couleur_texte, font=("Consolas", 14, "bold"))
    
    def on_enter(e):
        canvas.itemconfig(rect_id, fill=couleur_hover, outline=couleur_hover)
        
    def on_leave(e):
        canvas.itemconfig(rect_id, fill=couleur, outline=couleur)
        
    def on_click(e):
        # Simuler un 'clic' en déplaçant légèrement le bouton
        canvas.move(rect_id, 1, 1)
        canvas.move(text_id, 1, 1)
        command()
        canvas.after(100, lambda: [canvas.move(rect_id, -1, -1), canvas.move(text_id, -1, -1)])
        
    canvas.tag_bind(rect_id, "<Button-1>", on_click)
    canvas.tag_bind(text_id, "<Button-1>", on_click)
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    return canvas

# ==========================================
# Poker UI modernisée (mise à jour)
# ==========================================
class PokerApp:
    # --- PALETTE DE COULEURS ---
    COLOR_BG = "#1e1e1e"        # Fond principal (sombre)
    COLOR_CARD_FRAME = "#2c2c2c" # Fond des zones de cartes
    COLOR_LUIGI = "#E91E63"     # Magenta (accent Luigi/action principale)
    COLOR_PLAYER = "#00BCD4"    # Cyan (accent joueur/confirmation)
    COLOR_TEXT = "white"
    COLOR_SOLDE = "#FFEB3B"     # Jaune (solde/mise)
    COLOR_ACCENT = "#FF9800"    # Orange (mise boutons)

    def __init__(self, root):
        self.root = root
        self.root.title("Poker Luigi 🎲 - Style Amélioré")
        ico_path = os.path.join(dossier_script, "images", "ico.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        
        self.root.geometry("1200x850")
        self.root.config(bg=self.COLOR_BG)
        self.mario_font = ("Consolas", 16, "bold")
        self.radius = 12

        jouer_musique_fond()

        solde_joueur, solde_luigi = charger_solde()
        self.partie = PartiePoker(solde_joueur, solde_luigi)
        self.partie.distribuer()
        self.echange_effectue = False
        self.mise = 10
        self.mise_max = 30
        
        # --- FRAME PRINCIPALE (CONTENEUR) ---
        # Utiliser un conteneur principal pour mieux organiser le placement
        self.main_container = tk.Frame(root, bg=self.COLOR_BG)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # --- Zones de cartes ---
        self.frame_luigi = tk.Frame(self.main_container, bg=self.COLOR_CARD_FRAME, padx=15, pady=15, relief="flat", bd=0, highlightbackground="#333", highlightthickness=1)
        self.frame_joueur = tk.Frame(self.main_container, bg=self.COLOR_CARD_FRAME, padx=15, pady=15, relief="flat", bd=0, highlightbackground="#333", highlightthickness=1)
        
        self.frame_luigi.pack(pady=20, fill="x")
        self.frame_joueur.pack(pady=20, fill="x")
        
        # Chargement des images (inchangé mais important de le laisser ici)
        valeurs_images = {
            '7': '7.png', '8': '8.png', '9': '9.png', '10': '10.png',
            'Valet': 'champi.png', 'Dame': 'fleur.png', 'Roi': 'mario.png', 'As': 'etoile.png'
        }
        self.images_cartes_joueur = {}
        self.images_cartes_luigi = {}
        # ... (le code de chargement d'image avec arrondi PIL est conservé) ...
        for valeur, fichier in valeurs_images.items():
            chemin = os.path.join(dossier_images, fichier)
            if os.path.exists(chemin):
                img = Image.open(chemin).convert("RGBA")
                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0,0,img.width,img.height), radius=self.radius, fill=255)
                img.putalpha(mask)
                self.images_cartes_joueur[valeur] = ImageTk.PhotoImage(img)
                self.images_cartes_luigi[valeur] = ImageTk.PhotoImage(img)
            else:
                self.images_cartes_joueur[valeur] = None
                self.images_cartes_luigi[valeur] = None

        chemin_dos = os.path.join(dossier_images, "dos.png")
        if os.path.exists(chemin_dos):
            img_dos = Image.open(chemin_dos).convert("RGBA")
            mask = Image.new("L", img_dos.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0,0,img_dos.width,img_dos.height), radius=self.radius, fill=255)
            img_dos.putalpha(mask)
            self.image_dos = ImageTk.PhotoImage(img_dos)
        else:
            self.image_dos = None
        # Fin chargement images
        
        # --- Luigi (Haut) ---
        self.label_luigi = tk.Label(self.frame_luigi, text="♠ Cartes de Luigi ♠ :", fg=self.COLOR_LUIGI, bg=self.COLOR_CARD_FRAME, font=self.mario_font)
        self.label_luigi.pack(pady=(0, 10))
        self.frame_luigi_cartes = tk.Frame(self.frame_luigi, bg=self.COLOR_CARD_FRAME)
        self.frame_luigi_cartes.pack()
        
        for i in range(5):
            lbl = tk.Label(self.frame_luigi_cartes, image=self.image_dos, bg=self.COLOR_CARD_FRAME)
            lbl.image = self.image_dos
            lbl.grid(row=0, column=i, padx=8)

        # --- Séparateur central ---
        tk.Frame(self.main_container, height=2, bg="#333333").pack(fill="x", pady=25)
        
        # --- Actions et Statut ---
        self.frame_statut_actions = tk.Frame(self.main_container, bg=self.COLOR_BG)
        self.frame_statut_actions.pack(fill="x")
        
        # Sous-frame pour la mise (à gauche)
        self.frame_mise = tk.Frame(self.frame_statut_actions, bg=self.COLOR_BG)
        self.frame_mise.pack(side="left", padx=50)
        self.label_mise = tk.Label(self.frame_mise, text=f"💎 Mise : {self.mise}", fg=self.COLOR_SOLDE, bg=self.COLOR_BG, font=self.mario_font)
        self.label_mise.pack(pady=5)
        
        self.frame_boutons_mise = tk.Frame(self.frame_mise, bg=self.COLOR_BG)
        self.frame_boutons_mise.pack(pady=5)
        self.bouton_moins = bouton_arrondi(self.frame_boutons_mise, " -10 ", self.diminuer_mise, largeur=60, couleur=self.COLOR_ACCENT, couleur_hover="#FFB300", hauteur=35, couleur_texte=self.COLOR_TEXT)
        self.bouton_moins.pack(side="left", padx=5)
        self.bouton_plus = bouton_arrondi(self.frame_boutons_mise, " +10 ", self.augmenter_mise, largeur=60, couleur=self.COLOR_ACCENT, couleur_hover="#FFB300", hauteur=35, couleur_texte=self.COLOR_TEXT)
        self.bouton_plus.pack(side="left", padx=5)
        
        # Sous-frame pour les boutons d'action (au centre)
        self.frame_actions = tk.Frame(self.frame_statut_actions, bg=self.COLOR_BG)
        self.frame_actions.pack(side="left", padx=50)

        self.bouton_echanger = bouton_arrondi(self.frame_actions, "🔄 Échanger les cartes", self.echanger, couleur=self.COLOR_LUIGI, couleur_hover="#F06292", couleur_texte=self.COLOR_TEXT)
        self.bouton_echanger.pack(side="left", padx=20)

        self.bouton_valider = bouton_arrondi(self.frame_actions, "✅ Valider la main", self.valider, couleur=self.COLOR_PLAYER, couleur_hover="#4DD0E1", couleur_texte=self.COLOR_TEXT)
        self.bouton_valider.pack(side="left", padx=20)
        
        # Sous-frame pour le solde (à droite)
        self.frame_solde = tk.Frame(self.frame_statut_actions, bg=self.COLOR_BG)
        self.frame_solde.pack(side="right", padx=50)
        self.label_solde = tk.Label(self.frame_solde, text=f"💰 Ton solde : {self.partie.joueur.solde}\n👑 Luigi : {self.partie.luigi.solde}",
                                    fg=self.COLOR_SOLDE, bg=self.COLOR_BG, font=self.mario_font, justify=tk.LEFT)
        self.label_solde.pack(side="right")
        
        # --- Résultat (Entre actions et joueur) ---
        self.label_resultat = tk.Label(self.main_container, text="", fg="white", bg=self.COLOR_BG, font=self.mario_font)
        self.label_resultat.pack(pady=15)
        
        # --- Joueur (Bas) ---
        self.label_joueur = tk.Label(self.frame_joueur, text="♣ Tes cartes ♣ :", fg=self.COLOR_PLAYER, bg=self.COLOR_CARD_FRAME, font=self.mario_font)
        self.label_joueur.pack(pady=(0, 10))
        self.frame_cartes = tk.Frame(self.frame_joueur, bg=self.COLOR_CARD_FRAME)
        self.frame_cartes.pack()
        self.selection = set()
        self.afficher_cartes()

    # ==========================================
    # Affichage cartes joueur (modifié pour l'esthétique)
    # ==========================================
    def afficher_cartes(self):
        for widget in self.frame_cartes.winfo_children():
            widget.destroy()
            
        self.boutons_cartes = []
        while len(self.partie.joueur.main.cartes) < 5:
            self.partie.joueur.main.ajouter(self.partie.jeu.piocher())

        for i, c in enumerate(self.partie.joueur.main.cartes):
            img = self.images_cartes_joueur.get(c.valeur)
            
            # Contour pour la sélection
            couleur_contour = self.COLOR_LUIGI if i in self.selection else self.COLOR_CARD_FRAME
            
            # Relief pour simuler la profondeur lors de la sélection
            relief_type = tk.RAISED if i in self.selection else tk.FLAT
            border_width = 4 if i in self.selection else 1

            btn = tk.Label(self.frame_cartes, image=img, bg=self.COLOR_CARD_FRAME, bd=border_width,
                           relief=relief_type, highlightthickness=0, highlightbackground=couleur_contour)
            
            btn.image = img
            btn.grid(row=0, column=i, padx=15, pady=5)
            btn.bind("<Button-1>", lambda e, i=i: self.toggle_selection(i))
            self.boutons_cartes.append(btn)

    def toggle_selection(self, i):
        if self.echange_effectue:
            messagebox.showwarning("Attention", "L'échange est terminé pour cette manche.")
            return
        
        if i in self.selection:
            self.selection.remove(i)
        else:
            self.selection.add(i)
        self.afficher_cartes()

    # ==========================================
    # Échange et validation (mise à jour du solde)
    # ==========================================
    def echanger(self):
        if self.echange_effectue:
            messagebox.showwarning("Info", "Tu as déjà échangé tes cartes.")
            return
        if not self.selection:
            # L'échange sans sélection est une validation de la main initiale
            self.valider()
            return
            
        self.partie.echanger_cartes(list(self.selection))
        self.selection.clear()
        self.afficher_cartes()
        self.echange_effectue = True
        messagebox.showinfo("Info", f"Cartes échangées : Tu peux maintenant Valider la main.")

    def valider(self):
        if not self.echange_effectue:
             # Si le joueur n'a pas échangé, c'est comme s'il avait "passé" son tour d'échange
             self.echange_effectue = True
             
        # Désactiver les boutons pendant la validation et l'attente
        self.bouton_echanger.config(state=tk.DISABLED)
        self.bouton_valider.config(state=tk.DISABLED)
        self.bouton_plus.config(state=tk.DISABLED)
        self.bouton_moins.config(state=tk.DISABLED)
        
        # 1. Luigi joue
        self.partie.tour_luigi()
        
        # 2. Comparaison (inclut la gestion des gains/pertes)
        resultat = self.partie.comparer(self.mise)
        self.label_resultat.config(text=resultat)
        
        # 3. Afficher les cartes de Luigi
        for widget in self.frame_luigi_cartes.winfo_children():
            widget.destroy()
        for i, c in enumerate(self.partie.luigi.main.cartes):
            img = self.images_cartes_luigi.get(c.valeur)
            lbl = tk.Label(self.frame_luigi_cartes, image=img, bg=self.COLOR_CARD_FRAME)
            lbl.image = img
            lbl.grid(row=0, column=i, padx=8)

        # 4. Mettre à jour et sauvegarder le solde
        self.label_solde.config(text=f"💰 Ton solde : {self.partie.joueur.solde}\n👑 Luigi : {self.partie.luigi.solde}")
        sauvegarder_solde(self.partie.joueur.solde, self.partie.luigi.solde)

        # 5. Nouvelle manche après délai (plus long pour laisser le temps de lire)
        self.root.after(5000, self.nouvelle_manche)
        
    def nouvelle_manche(self):
        # Vérification de la fin de jeu
        if self.partie.joueur.solde <= 0 or self.partie.luigi.solde <= 0:
            message = "GAME OVER ! Luigi a gagné toutes tes pièces !" if self.partie.joueur.solde <= 0 else "VICTOIRE ! Tu as plumé Luigi !"
            messagebox.showinfo("Fin de Partie", message)
            self.root.destroy()
            return

        # Réinitialisation de la partie
        solde_joueur, solde_luigi = self.partie.joueur.solde, self.partie.luigi.solde
        self.partie = PartiePoker(solde_joueur, solde_luigi)
        self.partie.distribuer()
        
        self.echange_effectue = False
        self.selection.clear()
        self.afficher_cartes()

        # Luigi reset cartes dos
        for widget in self.frame_luigi_cartes.winfo_children():
            widget.destroy()
        for i in range(5):
            lbl = tk.Label(self.frame_luigi_cartes, image=self.image_dos, bg=self.COLOR_CARD_FRAME)
            lbl.image = self.image_dos
            lbl.grid(row=0, column=i, padx=8)

        # Réinitialisation des labels et de la mise
        self.label_resultat.config(text="Nouvelle manche ! Choisis tes cartes à échanger.")
        self.label_solde.config(text=f"💰 Ton solde : {self.partie.joueur.solde}\n👑 Luigi : {self.partie.luigi.solde}")
        self.label_mise.config(text=f"💎 Mise : {self.mise}")
        
        # Réactiver les boutons
        self.bouton_echanger.config(state=tk.NORMAL)
        self.bouton_valider.config(state=tk.NORMAL)
        self.bouton_plus.config(state=tk.NORMAL)
        self.bouton_moins.config(state=tk.NORMAL)

    # ==========================================
    # Gestion mise
    # ==========================================
    def augmenter_mise(self):
        if self.echange_effectue:
            messagebox.showwarning("Attention", "La mise ne peut être changée qu'au début de la manche.")
            return
        
        nouvelle_mise = self.mise + 10
        if nouvelle_mise <= self.partie.joueur.solde and nouvelle_mise <= self.mise_max:
            self.mise = nouvelle_mise
            self.label_mise.config(text=f"💎 Mise : {self.mise}")
        elif nouvelle_mise > self.mise_max:
            messagebox.showwarning("Mise Max", f"La mise maximum est de {self.mise_max}.")
        else:
            messagebox.showwarning("Solde", "Tu n'as pas assez de pièces pour cette mise.")

    def diminuer_mise(self):
        if self.echange_effectue:
            messagebox.showwarning("Attention", "La mise ne peut être changée qu'au début de la manche.")
            return
            
        if self.mise - 10 >= 10:
            self.mise -= 10
            self.label_mise.config(text=f"💎 Mise : {self.mise}")
        else:
            messagebox.showwarning("Mise Min", "La mise minimum est de 10.")

# ==========================================
# Programme principal
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    ico_path = os.path.join(dossier_script, "images", "ico.ico")
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass
    app = PokerApp(root)
    jouer_son(SON_START)
    root.mainloop()