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
# Logique du jeu
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
        for _ in range(5):
            self.joueur.main.ajouter(self.jeu.piocher())
            self.luigi.main.ajouter(self.jeu.piocher())
            jouer_son(SON_DISTRIB)

    def echanger_cartes(self, indices):
        for i in indices:
            self.joueur.main.cartes[i] = self.jeu.piocher()

    def tour_luigi(self):
        score, type_main, ordre = self.luigi.main.evaluer_main()
        cartes_a_echanger = []
        if score < 4:
            cartes_a_echanger = sorted(range(5), key=lambda i: self.luigi.main.cartes[i].valeur_num())[:3]
        for i in cartes_a_echanger:
            self.luigi.main.cartes[i] = self.jeu.piocher()

    def comparer(self, mise):
        s_j, t_j, v_j = self.joueur.main.evaluer_main()
        s_l, t_l, v_l = self.luigi.main.evaluer_main()
        if s_j > s_l or (s_j == s_l and v_j > v_l):
            self.joueur.recevoir_gain(mise)
            jouer_son(SON_VICTOIRE)
            jouer_son(SON_CLAP)
            return f"🎉 Tu gagnes ! ({t_j} contre {t_l})"
        elif s_j < s_l or (s_j == s_l and v_j < v_l):
            self.joueur.solde -= mise
            self.luigi.recevoir_gain(mise)
            jouer_son(SON_DEFAITE)
            return f"😬 Luigi gagne... ({t_l} contre {t_j})"
        else:
            jouer_son(SON_EGALITE)
            return f"🤝 Égalité parfaite ! ({t_j})"

# ==========================================
# Bouton arrondi adaptatif
# ==========================================
def bouton_arrondi(parent, texte, command, hauteur=40, couleur="#FF5555", couleur_hover="#FF7777", largeur=None):
    if largeur is None:
        largeur = max(150, len(texte)*12)
    canvas = tk.Canvas(parent, width=largeur, height=hauteur, bg=parent["bg"], highlightthickness=0)
    radius = 8
    x0, y0, x1, y1 = 2, 2, largeur-2, hauteur-2
    # draw rounded rect approximation by rectangle here (kept simple)
    canvas.create_rectangle(x0, y0, x1, y1, fill=couleur, outline=couleur, width=0)
    text_id = canvas.create_text(largeur/2, hauteur/2, text=texte, fill="white", font=("Consolas", 14, "bold"))
    def on_enter(e):
        canvas.itemconfig("all", fill=couleur_hover)
    def on_leave(e):
        canvas.itemconfig("all", fill=couleur)
    canvas.bind("<Button-1>", lambda e: command())
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    return canvas

# ==========================================
# Poker UI modernisée
# ==========================================
class PokerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Luigi 🎲")
        # change path to your ico file
        ico_path = os.path.join(dossier_script, "images", "ico.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        self.root.geometry("1200x850")
        self.root.config(bg="#1a1a1a")
        self.mario_font = ("Consolas", 16, "bold")
        self.radius = 12

        jouer_musique_fond()

        solde_joueur, solde_luigi = charger_solde()
        self.partie = PartiePoker(solde_joueur, solde_luigi)
        self.partie.distribuer()
        self.echange_effectue = False
        self.mise = 10
        self.mise_max = 30

        # frames pour les zones de cartes
        self.frame_luigi = tk.Frame(root, bg="#222222", padx=15, pady=15, relief="ridge", bd=2)
        self.frame_joueur = tk.Frame(root, bg="#222222", padx=15, pady=15, relief="ridge", bd=2)
        self.frame_luigi.pack(pady=20, fill="x", padx=20)
        self.frame_joueur.pack(pady=20, fill="x", padx=20)

        # chargement images
        valeurs_images = {
            '7': '7.png', '8': '8.png', '9': '9.png', '10': '10.png',
            'Valet': 'champi.png', 'Dame': 'fleur.png', 'Roi': 'mario.png', 'As': 'etoile.png'
        }
        self.images_cartes_joueur = {}
        self.images_cartes_luigi = {}
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

        # Luigi
        self.label_luigi = tk.Label(self.frame_luigi, text="Cartes de Luigi :", fg="#FF5555", bg="#222222", font=self.mario_font)
        self.label_luigi.pack()
        self.frame_luigi_cartes = tk.Frame(self.frame_luigi, bg="#222222")
        self.frame_luigi_cartes.pack()
        for i in range(5):
            lbl = tk.Label(self.frame_luigi_cartes, image=self.image_dos, bg="#222222")
            lbl.image = self.image_dos
            lbl.grid(row=0, column=i, padx=5)

        # Joueur
        self.label_joueur = tk.Label(self.frame_joueur, text="Tes cartes :", fg="#55FF55", bg="#222222", font=self.mario_font)
        self.label_joueur.pack()
        self.frame_cartes = tk.Frame(self.frame_joueur, bg="#222222")
        self.frame_cartes.pack()
        self.selection = set()
        self.afficher_cartes()

        # ======= frame centralisée actions + solde =======
        self.frame_actions = tk.Frame(root, bg="#1a1a1a")
        self.frame_actions.pack(pady=15)

        # boutons - on récupère le canvas et on le pack
        self.bouton_echanger = bouton_arrondi(self.frame_actions, "Échanger les cartes", self.echanger, couleur="#FF5555", couleur_hover="#FF7777")
        self.bouton_echanger.pack(side="left", padx=10)

        self.bouton_valider = bouton_arrondi(self.frame_actions, "Valider la main", self.valider, couleur="#5555FF", couleur_hover="#7777FF")
        self.bouton_valider.pack(side="left", padx=10)

        # label solde sur la même ligne, placé à droite
        self.label_solde = tk.Label(self.frame_actions, text=f"💰 Ton solde : {self.partie.joueur.solde} | Luigi : {self.partie.luigi.solde}",
                                    fg="#FFFF55", bg="#1a1a1a", font=self.mario_font)
        self.label_solde.pack(side="left", padx=30)

        # résultat sous la ligne des actions
        self.label_resultat = tk.Label(root, text="", fg="white", bg="#1a1a1a", font=self.mario_font)
        self.label_resultat.pack(pady=15)

        # mise
        self.frame_mise = tk.Frame(root, bg="#1a1a1a")
        self.frame_mise.pack(pady=10)
        self.label_mise = tk.Label(self.frame_mise, text=f"💰 Mise : {self.mise}", fg="#55FFFF", bg="#1a1a1a", font=self.mario_font)
        self.label_mise.pack(side="left", padx=5)
        self.bouton_plus = bouton_arrondi(self.frame_mise, "+", self.augmenter_mise, largeur=40, couleur="#E4D90A", couleur_hover="#D3CA26")
        self.bouton_plus.pack(side="left", padx=5)
        self.bouton_moins = bouton_arrondi(self.frame_mise, "-", self.diminuer_mise, largeur=40, couleur="#E4D90A", couleur_hover="#D3CA26")
        self.bouton_moins.pack(side="left", padx=5)

    # ==========================================
    # Affichage cartes joueur
    # ==========================================
    def afficher_cartes(self):
        for widget in self.frame_cartes.winfo_children():
            widget.destroy()
        self.boutons_cartes = []
        # s'assurer d'avoir des cartes (au cas où)
        while len(self.partie.joueur.main.cartes) < 5:
            self.partie.joueur.main.ajouter(self.partie.jeu.piocher())

        for i, c in enumerate(self.partie.joueur.main.cartes):
            img = self.images_cartes_joueur.get(c.valeur)
            couleur_contour = "#FF2222" if i in self.selection else "#555"
            btn = tk.Label(self.frame_cartes, image=img, bg="#333333", bd=4,
                           relief="solid", highlightthickness=4, highlightbackground=couleur_contour)
            btn.image = img
            btn.grid(row=0, column=i, padx=10, pady=5)
            btn.bind("<Button-1>", lambda e, i=i: self.toggle_selection(i))
            self.boutons_cartes.append(btn)

    def toggle_selection(self, i):
        if self.echange_effectue:
            return
        if i in self.selection:
            self.selection.remove(i)
        else:
            self.selection.add(i)
        self.afficher_cartes()

    # ==========================================
    # Échange et validation
    # ==========================================
    def echanger(self):
        if self.echange_effectue:
            messagebox.showinfo("Info", "Tu as déjà échangé tes cartes.")
            return
        if not self.selection:
            messagebox.showinfo("Info", "Aucune carte sélectionnée.")
            return
        self.partie.echanger_cartes(list(self.selection))
        self.selection.clear()
        self.afficher_cartes()
        self.echange_effectue = True
        messagebox.showinfo("Info", "Cartes échangées !")

    def valider(self):
        self.partie.tour_luigi()
        resultat = self.partie.comparer(self.mise)
        self.label_resultat.config(text=resultat)
        self.label_solde.config(text=f"💰 Ton solde : {self.partie.joueur.solde} | Luigi : {self.partie.luigi.solde}")

        # afficher cartes de Luigi
        for widget in self.frame_luigi_cartes.winfo_children():
            widget.destroy()
        for i, c in enumerate(self.partie.luigi.main.cartes):
            img = self.images_cartes_luigi.get(c.valeur)
            lbl = tk.Label(self.frame_luigi_cartes, image=img, bg="#222222")
            lbl.image = img
            lbl.grid(row=0, column=i, padx=5)

        sauvegarder_solde(self.partie.joueur.solde, self.partie.luigi.solde)
        # nouvelle manche après délai
        self.root.after(5000, self.nouvelle_manche)

    def nouvelle_manche(self):
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
            lbl = tk.Label(self.frame_luigi_cartes, image=self.image_dos, bg="#222222")
            lbl.image = self.image_dos
            lbl.grid(row=0, column=i, padx=5)

        self.label_resultat.config(text="")
        self.label_solde.config(text=f"💰 Ton solde : {self.partie.joueur.solde} | Luigi : {self.partie.luigi.solde}")
        self.label_mise.config(text=f"💰 Mise : {self.mise}")

    # ==========================================
    # Gestion mise
    # ==========================================
    def augmenter_mise(self):
        if self.mise + 10 <= self.partie.joueur.solde and self.mise + 10 <= self.mise_max:
            self.mise += 10
            self.label_mise.config(text=f"💰 Mise : {self.mise}")

    def diminuer_mise(self):
        if self.mise - 10 >= 10:
            self.mise -= 10
            self.label_mise.config(text=f"💰 Mise : {self.mise}")

# ==========================================
# Programme principal
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    # icône (modifie le chemin si nécessaire)
    ico_path = os.path.join(dossier_script, "images", "ico.ico")
    if os.path.exists(ico_path):
        try:
            root.iconbitmap(ico_path)
        except Exception:
            pass
    app = PokerApp(root)
    jouer_son(SON_START)
    root.mainloop()
