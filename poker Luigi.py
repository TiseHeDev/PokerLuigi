# -*- coding: utf-8 -*-
"""
Poker Luigi - Interface graphique remaniée (Tkinter)
Remplace/colle ce fichier en lieu et place de ton script original.
Gardera la logique du jeu (mains, mise, sauvegarde) mais modernise l'UI.
"""

import tkinter as tk
from tkinter import messagebox, ttk
import random
import json
import os
from PIL import Image, ImageTk, ImageDraw, ImageFont
import pygame
import threading

# ------------------------
# Chemins
# ------------------------
dossier_script = os.path.dirname(os.path.abspath(__file__))
dossier_images = os.path.join(dossier_script, "images")
dossier_sons = os.path.join(dossier_script, "sons")
FICHIER_SOLDE = os.path.join(dossier_script, "solde.json")

# ------------------------
# Son / musique
# ------------------------
try:
    pygame.mixer.init()
except Exception as e:
    print("Impossible d'initialiser pygame.mixer:", e)

SON_VICTOIRE = os.path.join(dossier_sons, "victoire.wav")
SON_DEFAITE = os.path.join(dossier_sons, "defaite.wav")
SON_EGALITE = os.path.join(dossier_sons, "egalite.wav")
SON_CLAP = os.path.join(dossier_sons, "clap.wav")
SON_FOND = os.path.join(dossier_sons, "fond.mp3")
SON_START = os.path.join(dossier_sons, "start.wav")
SON_DISTRIB = os.path.join(dossier_sons, "card_distrib.wav")

def jouer_son(fichier):
    if not os.path.exists(fichier):
        return
    try:
        snd = pygame.mixer.Sound(fichier)
        snd.play()
    except Exception as e:
        print("Erreur lecture son :", e)

def jouer_musique_fond():
    if not os.path.exists(SON_FOND):
        return
    try:
        pygame.mixer.music.load(SON_FOND)
        pygame.mixer.music.set_volume(0.35)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print("Erreur musique fond :", e)

# Lance la musique dans un thread pour éviter de bloquer l'UI
threading.Thread(target=jouer_musique_fond, daemon=True).start()

# ------------------------
# Multiplicateurs & sauvegarde
# ------------------------
MULTIPLICATEURS = {
    "Carte haute": 1,
    "Paire": 2,
    "Double Paire": 3,
    "Brelan": 4,
    "Suite": 5,
    "Couleur": 6,
    "Full": 8,
    "Carré": 10,
    "Quinte Flush": 20
}

def charger_solde():
    if os.path.exists(FICHIER_SOLDE):
        try:
            with open(FICHIER_SOLDE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("joueur", 100), data.get("luigi", 100)
        except Exception:
            return 100, 100
    return 100, 100

def sauvegarder_solde(solde_joueur, solde_luigi):
    try:
        with open(FICHIER_SOLDE, "w", encoding="utf-8") as f:
            json.dump({"joueur": solde_joueur, "luigi": solde_luigi}, f)
    except Exception as e:
        print("Impossible de sauvegarder le solde :", e)

# ------------------------
# Logique du jeu (identique, légère refactor)
# ------------------------
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
        self.joueur.main.cartes = []
        self.luigi.main.cartes = []
        self.jeu.melanger()
        for _ in range(5):
            self.joueur.main.ajouter(self.jeu.piocher())
            self.luigi.main.ajouter(self.jeu.piocher())

    def echanger_cartes(self, indices):
        for i in indices:
            self.joueur.main.cartes[i] = self.jeu.piocher()

    def tour_luigi(self):
        score, type_main, ordre = self.luigi.main.evaluer_main()
        cartes_a_echanger = []
        if score < 4:
            indices_tries = sorted(range(5), key=lambda i: self.luigi.main.cartes[i].valeur_num())
            cartes_a_echanger = indices_tries[:3]
        for i in cartes_a_echanger:
            self.luigi.main.cartes[i] = self.jeu.piocher()

    def comparer(self, mise):
        s_j, t_j, v_j = self.joueur.main.evaluer_main()
        s_l, t_l, v_l = self.luigi.main.evaluer_main()

        if not self.joueur.miser(mise):
            return "Erreur de mise: Solde insuffisant !"

        mult_joueur = MULTIPLICATEURS.get(t_j, 1)
        mult_luigi = MULTIPLICATEURS.get(t_l, 1)

        if s_j > s_l:
            gain = mise * mult_joueur
            self.joueur.recevoir_gain(gain)
            jouer_son(SON_VICTOIRE)
            jouer_son(SON_CLAP)
            return f"🎉 Tu gagnes ! ({t_j} contre {t_l}) → Gain : {gain} pièces"

        elif s_j == s_l:
            if v_j > v_l:
                gain = mise * mult_joueur
                self.joueur.recevoir_gain(gain)
                jouer_son(SON_VICTOIRE)
                jouer_son(SON_CLAP)
                return f"🎉 Tu gagnes ! ({t_j} contre {t_l} - Carte Haute) → Gain : {gain} pièces"
            elif v_j < v_l:
                gain = mise * mult_luigi
                self.luigi.recevoir_gain(gain)
                jouer_son(SON_DEFAITE)
                return f"😬 Luigi gagne... ({t_l} contre {t_j} - Carte Haute) → Luigi gagne {gain} pièces"
            else:
                self.joueur.recevoir_gain(mise)
                jouer_son(SON_EGALITE)
                return f"🤝 Égalité parfaite ! ({t_j})"

        else:
            gain = mise * mult_luigi
            self.luigi.recevoir_gain(gain)
            jouer_son(SON_DEFAITE)
            return f"😬 Luigi gagne... ({t_l} contre {t_j}) → Luigi gagne {gain} pièces"

# ------------------------
# Widgets personnalisés (boutons arrondis, petites améliorations)
# ------------------------
def bouton_arrondi(parent, texte, command, largeur=180, hauteur=44,
                   couleur="#2E8B57", hover="#3CB371", texte_couleur="white", font=("Helvetica", 12, "bold")):
    """
    Retourne un Canvas jouant le rôle d'un bouton arrondi moderne.
    On attache .widget_click() pour compatibilité.
    """
    canvas = tk.Canvas(parent, width=largeur, height=hauteur, bg=parent["bg"], highlightthickness=0)
    radius = int(hauteur/2 - 4)
    x0, y0, x1, y1 = 2, 2, largeur-2, hauteur-2

    # Dessine un rectangle arrondi simple
    def draw(bg_color):
        canvas.delete("all")
        # coins arrondis : on dessine arcs + rectange central
        canvas.create_arc(x0, y0, x0+2*radius, y0+2*radius, start=90, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(x1-2*radius, y0, x1, y0+2*radius, start=0, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(x0, y1-2*radius, x0+2*radius, y1, start=180, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(x1-2*radius, y1-2*radius, x1, y1, start=270, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_rectangle(x0+radius, y0, x1-radius, y1, fill=bg_color, outline=bg_color)
        canvas.create_rectangle(x0, y0+radius, x1, y1-radius, fill=bg_color, outline=bg_color)
        canvas.create_text((largeur)//2, (hauteur)//2, text=texte, fill=texte_couleur, font=font)
    draw(couleur)

    def on_enter(_):
        draw(hover)
    def on_leave(_):
        draw(couleur)
    def on_click(e=None):
        # petite animation "press"
        canvas.scale("all", largeur//2, hauteur//2, 0.98, 0.98)
        canvas.after(90, lambda: canvas.scale("all", largeur//2, hauteur//2, 1/0.98, 1/0.98))
        try:
            command()
        except Exception as e:
            print("Erreur dans callback bouton:", e)

    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    canvas.bind("<Button-1>", on_click)
    # exposition d'une méthode pour compatibilité (si besoin)
    canvas.widget_click = on_click
    return canvas

# ------------------------
# UI moderne (refonte)
# ------------------------
class PokerAppModern:
    BG = "#0f1720"            # fond très sombre
    PANEL = "#121826"         # panneaux
    ACCENT = "#FFB86B"        # accent chaud
    PLAYER = "#66E0FF"
    LUIGI = "#FF7AB6"
    SOLDE = "#FFD166"
    TEXT = "white"
    CARD_RADIUS = 14

    def __init__(self, root):
        self.root = root
        self.root.title("Poker Luigi — Moderne")
        self.root.configure(bg=self.BG)
        self.root.geometry("1180x780")
        # icon (si présent)
        ico = os.path.join(dossier_images, "ico.ico")
        if os.path.exists(ico):
            try:
                self.root.iconbitmap(ico)
            except Exception:
                pass

        # Charger soldes + partie
        solde_j, solde_l = charger_solde()
        self.partie = PartiePoker(solde_j, solde_l)
        self.partie.distribuer()
        self.echange_effectue = False
        self.mise = 10
        self.mise_max = 30
        self.selection = set()

        # Préparer images cartes
        self._charger_images_cartes()

        # Layout principal
        self.container = tk.Frame(root, bg=self.BG)
        self.container.pack(fill="both", expand=True, padx=18, pady=18)

        # Header
        header = tk.Frame(self.container, bg=self.BG)
        header.pack(fill="x", pady=(0,12))
        title = tk.Label(header, text="Poker Luigi", font=("Segoe UI", 20, "bold"), fg=self.ACCENT, bg=self.BG)
        title.pack(side="left")
        sub = tk.Label(header, text="— 5-card draw simplifié —", font=("Segoe UI", 11), fg="#9aa4b2", bg=self.BG)
        sub.pack(side="left", padx=6)

        # Corps : Luigi en haut, joueur en bas
        body = tk.Frame(self.container, bg=self.BG)
        body.pack(fill="both", expand=True)

        # Panneau Luigi (top)
        self.pane_luigi = tk.Frame(body, bg=self.PANEL, bd=0, relief="flat")
        self.pane_luigi.pack(fill="x", pady=(0,12))
        self._construire_pane_joueur(self.pane_luigi, "Luigi", self.LUIGI, top=True)

        # Séparateur
        sep = tk.Frame(body, height=2, bg="#16202b")
        sep.pack(fill="x", pady=8)

        # Actions & statut (au centre)
        centre = tk.Frame(body, bg=self.BG)
        centre.pack(fill="x", pady=(4,12))
        self._construire_panel_actions(centre)

        # Panneau joueur (bottom)
        self.pane_joueur = tk.Frame(body, bg=self.PANEL, bd=0, relief="flat")
        self.pane_joueur.pack(fill="x", pady=(12,0))
        self._construire_pane_joueur(self.pane_joueur, "Toi", self.PLAYER, top=False)

        # Footer
        foot = tk.Frame(self.container, bg=self.BG)
        foot.pack(fill="x", pady=(12,0))


        # Afficher les cartes joueur + luigi
        self.afficher_cartes_joueur()
        self.masquer_cartes_luigi()

    # --------------------
    # Chargement d'images et assets
    # --------------------
    def _charger_images_cartes(self):
        # mapping valeur -> filename comme précédemment
        mapping = {
            '7': '7.png', '8': '8.png', '9': '9.png', '10': '10.png',
            'Valet': 'champi.png', 'Dame': 'fleur.png', 'Roi': 'mario.png', 'As': 'etoile.png'
        }
        self.images_cartes = {}
        self.images_dos = None
        # taille carte
        self.card_w, self.card_h = 120, 160
        for val, fname in mapping.items():
            path = os.path.join(dossier_images, fname)
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA").resize((self.card_w, self.card_h), Image.LANCZOS)
                    mask = Image.new("L", img.size, 0)
                    draw = ImageDraw.Draw(mask)
                    draw.rounded_rectangle((0,0,img.width,img.height), radius=self.CARD_RADIUS, fill=255)
                    img.putalpha(mask)
                    self.images_cartes[val] = ImageTk.PhotoImage(img)
                except Exception as e:
                    print("Erreur chargement image carte:", e)
                    self.images_cartes[val] = None
            else:
                self.images_cartes[val] = None

        # dos
        path_dos = os.path.join(dossier_images, "dos.png")
        if os.path.exists(path_dos):
            try:
                d = Image.open(path_dos).convert("RGBA").resize((self.card_w, self.card_h), Image.LANCZOS)
                mask = Image.new("L", d.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0,0,d.width,d.height), radius=self.CARD_RADIUS, fill=255)
                d.putalpha(mask)
                self.images_dos = ImageTk.PhotoImage(d)
            except Exception as e:
                print("Erreur chargement dos carte:", e)
                self.images_dos = None

    # --------------------
    # Construction des panneaux de joueur / luigi
    # --------------------
    def _construire_pane_joueur(self, parent, nom, couleur_label, top=True):
        # header du panneau
        header = tk.Frame(parent, bg=parent["bg"])
        header.pack(fill="x", pady=(10,8))
        label = tk.Label(header, text=f"{nom}", font=("Segoe UI", 14, "bold"), fg=couleur_label, bg=parent["bg"])
        label.pack(side="left", padx=12)
        if top:
            info = tk.Label(header, text="Cartes de l'adversaire", fg="#8f9aa6", bg=parent["bg"])
            info.pack(side="left", padx=8)
        else:
            info = tk.Label(header, text="Sélectionne les cartes à échanger", fg="#8f9aa6", bg=parent["bg"])
            info.pack(side="left", padx=10)

        # zone cartes
        frame_cards = tk.Frame(parent, bg=parent["bg"])
        frame_cards.pack(pady=(6,12), padx=8)
        if top:
            self.frame_luigi_cartes = frame_cards
        else:
            self.frame_joueur_cartes = frame_cards

    # --------------------
    # Panel central actions / mise / status
    # --------------------
    def _construire_panel_actions(self, parent):
        left = tk.Frame(parent, bg=self.BG)
        left.pack(side="left", padx=24)

        # Mise
        mise_frame = tk.Frame(left, bg=self.BG)
        mise_frame.pack(anchor="w")
        self.label_mise = tk.Label(mise_frame, text=f"Mise : {self.mise}", font=("Segoe UI", 13, "bold"), fg=self.SOLDE, bg=self.BG)
        self.label_mise.pack(side="left", padx=(0,16))

        minus = bouton_arrondi(mise_frame, " -10 ", self.diminuer_mise, largeur=70, hauteur=36,
                               couleur="#2f3b4a", hover="#3b4a5e", texte_couleur="white")
        minus.pack(side="left", padx=6)
        plus = bouton_arrondi(mise_frame, " +10 ", self.augmenter_mise, largeur=70, hauteur=36,
                              couleur="#2f3b4a", hover="#3b4a5e", texte_couleur="white")
        plus.pack(side="left", padx=6)

        # Boutons principaux
        center = tk.Frame(parent, bg=self.BG)
        center.pack(side="left", padx=80)

        self.btn_echanger = bouton_arrondi(center, "🔄 Échanger", self.echanger, largeur=220, hauteur=46,
                                           couleur=self.LUIGI, hover="#ff9ac7", texte_couleur="white",
                                           font=("Segoe UI", 12, "bold"))
        self.btn_echanger.pack(side="left", padx=12)

        self.btn_valider = bouton_arrondi(center, "✅ Valider la main", self.valider, largeur=220, hauteur=46,
                                          couleur=self.PLAYER, hover="#8ff1ff", texte_couleur="black",
                                          font=("Segoe UI", 12, "bold"))
        self.btn_valider.pack(side="left", padx=12)

        # Status & soldes (droite)
        right = tk.Frame(parent, bg=self.BG)
        right.pack(side="right", padx=18)
        self.label_status = tk.Label(right, text="Bonne chance !", font=("Segoe UI", 12), fg="#aab6c5", bg=self.BG)
        self.label_status.pack(anchor="e")
        solde_frame = tk.Frame(right, bg=self.BG)
        solde_frame.pack(anchor="e", pady=(6,0))
        self.label_solde = tk.Label(solde_frame, text=f"Ton solde : {self.partie.joueur.solde}\nLuigi : {self.partie.luigi.solde}",
                                    font=("Segoe UI", 11, "bold"), fg=self.SOLDE, bg=self.BG, justify="right")
        self.label_solde.pack(anchor="e")

    # --------------------
    # Affichage cartes joueur / luigi
    # --------------------
    def afficher_cartes_joueur(self):
        # vide
        for w in getattr(self, "frame_joueur_cartes").winfo_children():
            w.destroy()

        # garantir 5 cartes
        while len(self.partie.joueur.main.cartes) < 5:
            self.partie.joueur.main.ajouter(self.partie.jeu.piocher())

        self.boutons_cartes = []
        for i, c in enumerate(self.partie.joueur.main.cartes):
            imgtk = self.images_cartes.get(c.valeur)
            frame = tk.Frame(self.frame_joueur_cartes, bg=self.PANEL, padx=6, pady=6)
            frame.grid(row=0, column=i, padx=8)

            if imgtk:
                lbl = tk.Label(frame, image=imgtk, bg=self.PANEL)
                lbl.image = imgtk
            else:
                # fallback visuel si image manquante
                card = tk.Frame(frame, width=self.card_w, height=self.card_h, bg="#18202b")
                label_txt = tk.Label(card, text=f"{c.valeur}\n{c.couleur}", fg="white", bg="#18202b", font=("Segoe UI", 12, "bold"))
                label_txt.place(relx=0.5, rely=0.5, anchor="center")
                card.pack_propagate(False)
                card.grid_propagate(False)
                lbl = card

            # Border si sélection
            if i in self.selection:
                lbl.config(highlightthickness=4, highlightbackground=self.ACCENT)
            else:
                lbl.config(highlightthickness=1, highlightbackground="#0f1620")

            lbl.bind("<Button-1>", lambda e, idx=i: self.toggle_selection(idx))
            lbl.pack()
            self.boutons_cartes.append(lbl)

    def masquer_cartes_luigi(self):
        for w in getattr(self, "frame_luigi_cartes").winfo_children():
            w.destroy()
        for i in range(5):
            frame = tk.Frame(self.frame_luigi_cartes, bg=self.PANEL, padx=6, pady=6)
            frame.grid(row=0, column=i, padx=8)
            if self.images_dos:
                lbl = tk.Label(frame, image=self.images_dos, bg=self.PANEL)
                lbl.image = self.images_dos
                lbl.pack()
            else:
                placeholder = tk.Frame(frame, width=self.card_w, height=self.card_h, bg="#16202b")
                lbltxt = tk.Label(placeholder, text="🤫", font=("Segoe UI", 28), bg="#16202b")
                lbltxt.place(relx=0.5, rely=0.5, anchor="center")
                placeholder.pack()
        # status
        self.label_status.config(text="Cartes de Luigi cachées")

    def reveler_cartes_luigi(self):
        for w in getattr(self, "frame_luigi_cartes").winfo_children():
            w.destroy()
        for i, c in enumerate(self.partie.luigi.main.cartes):
            frame = tk.Frame(self.frame_luigi_cartes, bg=self.PANEL, padx=6, pady=6)
            frame.grid(row=0, column=i, padx=8)
            imgtk = self.images_cartes.get(c.valeur)
            if imgtk:
                lbl = tk.Label(frame, image=imgtk, bg=self.PANEL)
                lbl.image = imgtk
                lbl.pack()
            else:
                placeholder = tk.Frame(frame, width=self.card_w, height=self.card_h, bg="#16202b")
                label_txt = tk.Label(placeholder, text=f"{c.valeur}\n{c.couleur}", fg="white", bg="#16202b", font=("Segoe UI", 12, "bold"))
                label_txt.place(relx=0.5, rely=0.5, anchor="center")
                placeholder.pack()
        self.label_status.config(text="Luigi a joué — Résultat ci-dessous")

    # --------------------
    # Actions utilisateur
    # --------------------
    def toggle_selection(self, i):
        if self.echange_effectue:
            messagebox.showwarning("Attention", "L'échange est terminé pour cette manche.")
            return
        if i in self.selection:
            self.selection.remove(i)
        else:
            self.selection.add(i)
        self.afficher_cartes_joueur()

    def echanger(self):
        if self.echange_effectue:
            messagebox.showwarning("Info", "Tu as déjà échangé tes cartes.")
            return
        if not self.selection:
            # si aucune sélection -> on considère que le joueur passe à la validation
            self.valider()
            return
        self.partie.echanger_cartes(sorted(list(self.selection)))
        self.selection.clear()
        self.echange_effectue = True
        jouer_son(SON_DISTRIB)
        self.afficher_cartes_joueur()
        self.label_status.config(text="Cartes échangées — Valide ta main ou attends la résolution")

    def valider(self):
        # On verrouille les actions
        self._set_buttons_state(False)
        if not self.echange_effectue:
            self.echange_effectue = True

        # Luigi joue
        self.partie.tour_luigi()
        # Revele animations sonores
        jouer_son(SON_DISTRIB)
        # Compare / résultat
        resultat = self.partie.comparer(self.mise)
        # update UI
        self.reveler_cartes_luigi()
        self.label_status.config(text=resultat)
        self.label_solde.config(text=f"Ton solde : {self.partie.joueur.solde}\nLuigi : {self.partie.luigi.solde}")
        sauvegarder_solde(self.partie.joueur.solde, self.partie.luigi.solde)

        # Nouvelle manche après délai (mais on ne bloque la boucle UI : on utilise after)
        self.root.after(3800, self.nouvelle_manche)

            # --------------------
    # Écrans de victoire / défaite / égalité
    # --------------------
    def afficher_ecran_fin(self, etat, texte):
        """
        etat = 'win' | 'lose' | 'draw'
        texte = texte à afficher
        """
        # Overlay semi-transparent
        overlay = tk.Frame(self.root, bg="#000000", width=self.root.winfo_width(),
                           height=self.root.winfo_height(), opacity=0.4)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Couleurs selon résultat
        if etat == "win":
            couleur = "#5CFF91"
        elif etat == "lose":
            couleur = "#FF6B6B"
        else:
            couleur = "#FFD166"

        # Box centrale
        box = tk.Frame(overlay, bg="#1a2332", bd=0)
        box.place(relx=0.5, rely=0.5, anchor="center")

        lbl = tk.Label(box, text=texte,
                       font=("Segoe UI", 22, "bold"),
                       fg=couleur, bg="#1a2332")
        lbl.pack(padx=40, pady=30)

        # Petite animation de zoom
        def anim(scale=0.6):
            if scale >= 1:
                return
            box.scale = scale
            box.tk.call("tk", "scaling", scale)
            self.root.after(16, lambda: anim(scale + 0.05))

        anim()

        # Remove overlay after delay
        self.root.after(2500, overlay.destroy)


    def nouvelle_manche(self):
        # Vérifier fin de jeu
        if self.partie.joueur.solde <= 0 or self.partie.luigi.solde <= 0:
            msg = "GAME OVER ! Luigi a gagné toutes tes pièces !" if self.partie.joueur.solde <= 0 else "VICTOIRE ! Tu as plumé Luigi !"
            messagebox.showinfo("Fin de Partie", msg)
            self.root.destroy()
            return

        solde_j, solde_l = self.partie.joueur.solde, self.partie.luigi.solde
        self.partie = PartiePoker(solde_j, solde_l)
        self.partie.distribuer()
        self.selection.clear()
        self.echange_effectue = False
        self.afficher_cartes_joueur()
        self.masquer_cartes_luigi()
        self.label_status.config(text="Nouvelle manche — Choisis tes cartes à échanger")
        self.label_mise.config(text=f"Mise : {self.mise}")
        self._set_buttons_state(True)

    def augmenter_mise(self):
        if self.echange_effectue:
            messagebox.showwarning("Attention", "La mise ne peut être changée qu'au début de la manche.")
            return
        nouvelle_mise = self.mise + 10
        if nouvelle_mise <= self.partie.joueur.solde and nouvelle_mise <= self.mise_max:
            self.mise = nouvelle_mise
            self.label_mise.config(text=f"Mise : {self.mise}")
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
            self.label_mise.config(text=f"Mise : {self.mise}")
        else:
            messagebox.showwarning("Mise Min", "La mise minimum est de 10.")

    def _set_buttons_state(self, enabled=True):
        state = tk.NORMAL if enabled else tk.DISABLED
        # nos boutons sont des Canvas : on peut remplacer par désactivation logique (unbind)
        if enabled:
            self.btn_echanger.bind("<Button-1>", lambda e=None: self.echanger())
            self.btn_valider.bind("<Button-1>", lambda e=None: self.valider())
        else:
            # noop binds (empêche l'action)
            self.btn_echanger.bind("<Button-1>", lambda e=None: None)
            self.btn_valider.bind("<Button-1>", lambda e=None: None)

# ------------------------
# Lancement
# ------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = PokerAppModern(root)
    # Son de démarrage
    jouer_son(SON_START)
    root.mainloop()
