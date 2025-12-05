# -*- coding: utf-8 -*-
"""
Poker Luigi - LAN Edition (Compatible EXE)
Solo vs Luigi OU Multijoueur en réseau local.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import random
import json
import os
import sys
from PIL import Image, ImageTk, ImageDraw
import pygame
import threading
import socket
import pickle
import time

# ------------------------
# Fonction magique pour le chemin des ressources (.exe)
# ------------------------
def resource_path(relative_path):
    """ Obtient le chemin absolu vers la ressource """
    try:
        # PyInstaller crée un dossier temporaire _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # CAS NORMAL (DEV): On utilise le dossier où se trouve le fichier .py
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# ------------------------
# Chemins
# ------------------------
# Pour les assets (lecture seule), on utilise resource_path
dossier_images = resource_path("images")
dossier_sons = resource_path("sons")

# Pour la sauvegarde (écriture), on utilise le dossier courant de l'exe (pas le dossier temporaire)
dossier_courant = os.path.dirname(os.path.abspath(sys.argv[0]))
FICHIER_SOLDE = os.path.join(dossier_courant, "solde.json")

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
    if not os.path.exists(fichier): return
    try:
        snd = pygame.mixer.Sound(fichier)
        snd.play()
    except: pass

def jouer_musique_fond():
    if not os.path.exists(SON_FOND): return
    try:
        pygame.mixer.music.load(SON_FOND)
        pygame.mixer.music.set_volume(0.35)
        pygame.mixer.music.play(-1)
    except: pass

# Lance la musique
threading.Thread(target=jouer_musique_fond, daemon=True).start()

# ------------------------
# Multiplicateurs & sauvegarde
# ------------------------
MULTIPLICATEURS = {
    "Carte haute": 1, "Paire": 2, "Double Paire": 3, "Brelan": 4,
    "Suite": 5, "Couleur": 6, "Full": 8, "Carré": 10, "Quinte Flush": 20
}

def charger_solde():
    if os.path.exists(FICHIER_SOLDE):
        try:
            with open(FICHIER_SOLDE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("joueur", 100), data.get("luigi", 100)
        except: return 100, 100
    return 100, 100

def sauvegarder_solde(solde_joueur, solde_luigi):
    try:
        with open(FICHIER_SOLDE, "w", encoding="utf-8") as f:
            json.dump({"joueur": solde_joueur, "luigi": solde_luigi}, f)
    except: pass

# ------------------------
# Logique du jeu
# ------------------------
class Carte:
    valeurs = ['7', '8', '9', '10', 'Valet', 'Dame', 'Roi', 'As']
    couleurs = ['♥', '♦', '♣', '♠']
    def __init__(self, valeur, couleur):
        self.valeur = valeur
        self.couleur = couleur
    def __repr__(self): return f"{self.valeur}{self.couleur}"
    def valeur_num(self): return Carte.valeurs.index(self.valeur)

class JeuDeCartes:
    def __init__(self):
        self.cartes = [Carte(v, c) for v in Carte.valeurs for c in Carte.couleurs]
        self.melanger()
    def melanger(self): random.shuffle(self.cartes)
    def piocher(self): return self.cartes.pop() if self.cartes else None

class MainJoueur:
    def __init__(self): self.cartes = []
    def ajouter(self, carte): self.cartes.append(carte)
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

        if flush and straight: return (8, "Quinte Flush", ordre_valeurs)
        elif unique_vals == 2:
            return (7, "Carré", ordre_valeurs) if any(valeurs.count(v) == 4 for v in valeurs) else (6, "Full", ordre_valeurs)
        elif flush: return (5, "Couleur", ordre_valeurs)
        elif straight: return (4, "Suite", ordre_valeurs)
        elif any(valeurs.count(v) == 3 for v in valeurs): return (3, "Brelan", ordre_valeurs)
        elif sum(1 for v in set(valeurs) if valeurs.count(v) == 2) == 2: return (2, "Double Paire", ordre_valeurs)
        elif any(valeurs.count(v) == 2 for v in valeurs): return (1, "Paire", ordre_valeurs)
        else: return (0, "Carte haute", ordre_valeurs)

class Joueur:
    def __init__(self, nom, solde=100):
        self.nom = nom
        self.solde = solde
        self.main = MainJoueur()
    def miser(self, montant):
        if montant > self.solde: return False
        self.solde -= montant
        return True
    def recevoir_gain(self, montant): self.solde += montant

# ------------------------
# Classe Réseau (LAN)
# ------------------------
class NetworkManager:
    def __init__(self, is_host, ip=None, port=5555):
        self.is_host = is_host
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = (ip, port) if ip else ('0.0.0.0', port)
        self.conn = None
        self.running = True
        self.queue = [] # File d'attente des messages reçus

    def start_host(self):
        try:
            self.client.bind(self.addr)
            self.client.listen(1)
            print("En attente de connexion...")
            self.conn, addr = self.client.accept()
            print(f"Connecté à {addr}")
            return True
        except Exception as e:
            print("Erreur Host:", e)
            return False

    def start_client(self):
        try:
            self.client.connect(self.addr)
            self.conn = self.client
            return True
        except Exception as e:
            print("Erreur Client:", e)
            return False

    def send(self, data):
        try:
            if self.conn:
                self.conn.send(pickle.dumps(data))
        except Exception as e:
            print("Erreur envoi:", e)

    def receive_loop(self, callback):
        while self.running:
            try:
                if self.conn:
                    data = self.conn.recv(4096)
                    if not data: break
                    obj = pickle.loads(data)
                    callback(obj)
            except:
                break

    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except: return "127.0.0.1"
    
    def close(self):
        self.running = False
        if self.conn: self.conn.close()
        if self.client: self.client.close()

# ------------------------
# Widgets Custom
# ------------------------
def bouton_arrondi(parent, texte, command, largeur=180, hauteur=44,
                   couleur="#2E8B57", hover="#3CB371", texte_couleur="white", font=("Helvetica", 12, "bold")):
    canvas = tk.Canvas(parent, width=largeur, height=hauteur, bg=parent["bg"], highlightthickness=0)
    radius = int(hauteur/2 - 4)
    x0, y0, x1, y1 = 2, 2, largeur-2, hauteur-2
    def draw(bg_color):
        canvas.delete("all")
        canvas.create_arc(x0, y0, x0+2*radius, y0+2*radius, start=90, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(x1-2*radius, y0, x1, y0+2*radius, start=0, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(x0, y1-2*radius, x0+2*radius, y1, start=180, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_arc(x1-2*radius, y1-2*radius, x1, y1, start=270, extent=90, fill=bg_color, outline=bg_color)
        canvas.create_rectangle(x0+radius, y0, x1-radius, y1, fill=bg_color, outline=bg_color)
        canvas.create_rectangle(x0, y0+radius, x1, y1-radius, fill=bg_color, outline=bg_color)
        canvas.create_text((largeur)//2, (hauteur)//2, text=texte, fill=texte_couleur, font=font)
    draw(couleur)
    def on_enter(_): draw(hover)
    def on_leave(_): draw(couleur)
    def on_click(e=None):
        canvas.scale("all", largeur//2, hauteur//2, 0.98, 0.98)
        canvas.after(90, lambda: canvas.scale("all", largeur//2, hauteur//2, 1/0.98, 1/0.98))
        if command: command()
    canvas.bind("<Enter>", on_enter)
    canvas.bind("<Leave>", on_leave)
    canvas.bind("<Button-1>", on_click)
    return canvas

# ------------------------
# Application Principale
# ------------------------
class PokerAppModern:
    BG = "#0f1720"
    PANEL = "#121826"
    ACCENT = "#FFB86B"
    PLAYER = "#66E0FF"
    LUIGI = "#FF7AB6"
    SOLDE = "#FFD166"
    CARD_RADIUS = 14

    def __init__(self, root, mode="solo", network=None):
        self.root = root
        self.mode = mode  # "solo" ou "lan"
        self.network = network
        
        self.root.title("Poker Luigi — " + ("LAN Multiplayer" if mode == "lan" else "Solo"))
        self.root.configure(bg=self.BG)
        self.root.geometry("1180x780")
        
        # Etats LAN
        self.lan_opponent_hand = None
        self.lan_my_hand_sent = False
        
        # Jeu
        solde_j, solde_l = charger_solde()
        self.partie = self.PartieWrapper(solde_j, solde_l)
        
        # Init Variables
        self.mise = 10
        self.mise_max = 30
        self.selection = set()
        self.echange_effectue = False

        self._charger_images_cartes()
        self.setup_ui()

        # Démarrage
        if self.mode == "solo":
            self.partie.distribuer()
            self.afficher_cartes_joueur()
            self.masquer_cartes_adversaire()
        elif self.mode == "lan":
            # Thread d'écoute réseau
            if self.network:
                threading.Thread(target=self.network.receive_loop, args=(self.on_network_message,), daemon=True).start()
            
            if self.network and self.network.is_host:
                self.lan_host_start_round()
            else:
                self.label_status.config(text="En attente de l'hôte pour commencer...")
                self._set_buttons_state(False)

    # Wrapper pour le jeu
    class PartieWrapper:
        def __init__(self, sj, sl):
            self.jeu = JeuDeCartes()
            self.joueur = Joueur("Toi", sj)
            self.luigi = Joueur("Adversaire", sl)
        
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
        
        def tour_luigi(self): # Mode Solo IA
            score, _, _ = self.luigi.main.evaluer_main()
            if score < 4:
                indices = sorted(range(5), key=lambda i: self.luigi.main.cartes[i].valeur_num())[:3]
                for i in indices: self.luigi.main.cartes[i] = self.jeu.piocher()

    # --------------------
    # UI Construction
    # --------------------
    def setup_ui(self):
        self.container = tk.Frame(self.root, bg=self.BG)
        self.container.pack(fill="both", expand=True, padx=18, pady=18)

        # Header
        header = tk.Frame(self.container, bg=self.BG)
        header.pack(fill="x", pady=(0,12))
        title = tk.Label(header, text="Poker Luigi", font=("Segoe UI", 20, "bold"), fg=self.ACCENT, bg=self.BG)
        title.pack(side="left")
        sub_text = "— LAN Multiplayer —" if self.mode == "lan" else "— 5-card draw simplifié —"
        sub = tk.Label(header, text=sub_text, font=("Segoe UI", 11), fg="#9aa4b2", bg=self.BG)
        sub.pack(side="left", padx=6)

        # Body
        body = tk.Frame(self.container, bg=self.BG)
        body.pack(fill="both", expand=True)

        # Adversaire (Haut)
        nom_adv = "Adversaire" if self.mode == "lan" else "Luigi"
        self.pane_luigi = tk.Frame(body, bg=self.PANEL)
        self.pane_luigi.pack(fill="x", pady=(0,12))
        self._construire_pane(self.pane_luigi, nom_adv, self.LUIGI, top=True)

        # Actions (Centre)
        centre = tk.Frame(body, bg=self.BG)
        centre.pack(fill="x", pady=(4,12))
        self._construire_actions(centre)

        # Joueur (Bas)
        self.pane_joueur = tk.Frame(body, bg=self.PANEL)
        self.pane_joueur.pack(fill="x", pady=(12,0))
        self._construire_pane(self.pane_joueur, "Toi", self.PLAYER, top=False)

    def _construire_pane(self, parent, nom, color, top):
        tk.Label(parent, text=nom, font=("Segoe UI", 14, "bold"), fg=color, bg=self.PANEL).pack(anchor="w", padx=12, pady=(10,0))
        frame_cards = tk.Frame(parent, bg=self.PANEL)
        frame_cards.pack(pady=10)
        if top: self.frame_luigi_cartes = frame_cards
        else: self.frame_joueur_cartes = frame_cards

    def _construire_actions(self, parent):
        # Mise (désactivée en LAN pour simplifier la synchro V1)
        if self.mode == "solo":
            left = tk.Frame(parent, bg=self.BG)
            left.pack(side="left", padx=24)
            self.label_mise = tk.Label(left, text=f"Mise : {self.mise}", font=("Segoe UI", 13, "bold"), fg=self.SOLDE, bg=self.BG)
            self.label_mise.pack(side="left", padx=(0,16))
            bouton_arrondi(left, " -10 ", self.diminuer_mise, 70, 36, "#2f3b4a", "#3b4a5e").pack(side="left", padx=6)
            bouton_arrondi(left, " +10 ", self.augmenter_mise, 70, 36, "#2f3b4a", "#3b4a5e").pack(side="left", padx=6)
        else:
            # En LAN, mise fixe pour simplifier
            tk.Label(parent, text="Mise Fixe: 10", font=("Segoe UI", 13), fg=self.SOLDE, bg=self.BG).pack(side="left", padx=24)

        # Boutons
        center = tk.Frame(parent, bg=self.BG)
        center.pack(side="left", padx=80)
        self.btn_echanger = bouton_arrondi(center, "🔄 Échanger", self.echanger, 220, 46, self.LUIGI, "#ff9ac7")
        self.btn_echanger.pack(side="left", padx=12)
        self.btn_valider = bouton_arrondi(center, "✅ Valider la main", self.valider, 220, 46, self.PLAYER, "#8ff1ff", texte_couleur="black")
        self.btn_valider.pack(side="left", padx=12)

        # Status
        right = tk.Frame(parent, bg=self.BG)
        right.pack(side="right", padx=18)
        self.label_status = tk.Label(right, text="Bonne chance !", font=("Segoe UI", 12), fg="#aab6c5", bg=self.BG)
        self.label_status.pack(anchor="e")
        self.label_solde = tk.Label(right, text=f"Toi: {self.partie.joueur.solde} | Adv: {self.partie.luigi.solde}",
                                    font=("Segoe UI", 11, "bold"), fg=self.SOLDE, bg=self.BG)
        self.label_solde.pack(anchor="e")

    def _charger_images_cartes(self):
        mapping = {'7': '7.png', '8': '8.png', '9': '9.png', '10': '10.png',
                   'Valet': 'champi.png', 'Dame': 'fleur.png', 'Roi': 'mario.png', 'As': 'etoile.png'}
        self.images_cartes = {}
        self.card_w, self.card_h = 120, 160
        
        def process_img(path):
            try:
                img = Image.open(path).convert("RGBA").resize((self.card_w, self.card_h), Image.LANCZOS)
                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0,0,img.width,img.height), radius=self.CARD_RADIUS, fill=255)
                img.putalpha(mask)
                return ImageTk.PhotoImage(img)
            except: return None

        for val, fname in mapping.items():
            path = os.path.join(dossier_images, fname)
            if os.path.exists(path): self.images_cartes[val] = process_img(path)
            else: self.images_cartes[val] = None
        
        path_dos = os.path.join(dossier_images, "dos.png")
        self.images_dos = process_img(path_dos) if os.path.exists(path_dos) else None

    # --------------------
    # Affichage
    # --------------------
    def afficher_cartes_joueur(self):
        for w in self.frame_joueur_cartes.winfo_children(): w.destroy()
        while len(self.partie.joueur.main.cartes) < 5:
            self.partie.joueur.main.ajouter(self.partie.jeu.piocher())

        for i, c in enumerate(self.partie.joueur.main.cartes):
            imgtk = self.images_cartes.get(c.valeur)
            frame = tk.Frame(self.frame_joueur_cartes, bg=self.PANEL, padx=6, pady=6)
            frame.grid(row=0, column=i, padx=8)
            
            if imgtk:
                lbl = tk.Label(frame, image=imgtk, bg=self.PANEL)
                lbl.image = imgtk
            else:
                card = tk.Frame(frame, width=self.card_w, height=self.card_h, bg="#18202b")
                tk.Label(card, text=f"{c.valeur}\n{c.couleur}", fg="white", bg="#18202b").place(relx=0.5, rely=0.5, anchor="center")
                card.pack_propagate(False)
                lbl = card
            
            if i in self.selection: lbl.config(highlightthickness=4, highlightbackground=self.ACCENT)
            else: lbl.config(highlightthickness=1, highlightbackground="#0f1620")
            
            lbl.bind("<Button-1>", lambda e, idx=i: self.toggle_selection(idx))
            lbl.pack()

    def masquer_cartes_adversaire(self):
        for w in self.frame_luigi_cartes.winfo_children(): w.destroy()
        for i in range(5):
            frame = tk.Frame(self.frame_luigi_cartes, bg=self.PANEL, padx=6, pady=6)
            frame.grid(row=0, column=i, padx=8)
            if self.images_dos:
                lbl = tk.Label(frame, image=self.images_dos, bg=self.PANEL)
                lbl.image = self.images_dos
                lbl.pack()
            else:
                placeholder = tk.Frame(frame, width=self.card_w, height=self.card_h, bg="#16202b")
                tk.Label(placeholder, text="?", font=("Segoe UI", 28), bg="#16202b").place(relx=0.5, rely=0.5, anchor="center")
                placeholder.pack()

    def reveler_cartes_adversaire(self):
        for w in self.frame_luigi_cartes.winfo_children(): w.destroy()
        # En LAN, on utilise la main reçue
        main_adv = self.lan_opponent_hand.cartes if self.mode == "lan" else self.partie.luigi.main.cartes
        
        for i, c in enumerate(main_adv):
            frame = tk.Frame(self.frame_luigi_cartes, bg=self.PANEL, padx=6, pady=6)
            frame.grid(row=0, column=i, padx=8)
            imgtk = self.images_cartes.get(c.valeur)
            if imgtk:
                lbl = tk.Label(frame, image=imgtk, bg=self.PANEL)
                lbl.image = imgtk
                lbl.pack()
            else:
                p = tk.Frame(frame, width=self.card_w, height=self.card_h, bg="#16202b")
                tk.Label(p, text=f"{c.valeur}\n{c.couleur}", fg="white", bg="#18202b").pack()
                p.pack()

    # --------------------
    # Logique Réseau (LAN)
    # --------------------
    def lan_host_start_round(self):
        # L'hôte génère tout
        self.partie.jeu.melanger()
        hand_host = [self.partie.jeu.piocher() for _ in range(5)]
        hand_client = [self.partie.jeu.piocher() for _ in range(5)]
        
        self.partie.joueur.main.cartes = hand_host
        self.afficher_cartes_joueur()
        self.masquer_cartes_adversaire()
        self._set_buttons_state(True)
        self.label_status.config(text="Nouvelle manche LAN !")

        # Envoyer au client
        msg = {"type": "START", "hand": hand_client}
        self.network.send(msg)

    def on_network_message(self, data):
        # Callback threadé -> utiliser after pour update UI
        self.root.after(0, lambda: self.handle_message(data))

    def handle_message(self, data):
        msg_type = data.get("type")
        
        if msg_type == "START":
            # Le client reçoit sa main initiale
            self.partie.joueur.main.cartes = data.get("hand")
            self.afficher_cartes_joueur()
            self.masquer_cartes_adversaire()
            self._set_buttons_state(True)
            self.label_status.config(text="C'est parti ! Choisis tes cartes.")
            self.echange_effectue = False
            self.lan_opponent_hand = None
            self.lan_my_hand_sent = False
        
        elif msg_type == "HAND":
            # L'adversaire a envoyé sa main finale
            self.lan_opponent_hand = MainJoueur()
            self.lan_opponent_hand.cartes = data.get("hand_obj")
            
            if self.lan_my_hand_sent:
                # Si j'ai déjà joué, on résout
                self.resolve_lan_round()
            else:
                self.label_status.config(text="L'adversaire a validé. À toi !")

    def resolve_lan_round(self):
        self.reveler_cartes_adversaire()
        
        s_j, t_j, v_j = self.partie.joueur.main.evaluer_main()
        s_l, t_l, v_l = self.lan_opponent_hand.evaluer_main()
        
        mise = 10 # Fixe en LAN pour l'instant
        mult_joueur = MULTIPLICATEURS.get(t_j, 1)
        mult_luigi = MULTIPLICATEURS.get(t_l, 1) # Multiplicateur adverse

        msg = ""
        gain = 0
        
        # Logique comparaison
        win = False
        draw = False
        
        if s_j > s_l: win = True
        elif s_j == s_l:
            if v_j > v_l: win = True
            elif v_j == v_l: draw = True
        
        if draw:
            msg = f"🤝 Égalité ({t_j})"
            jouer_son(SON_EGALITE)
        elif win:
            gain = mise * mult_joueur
            self.partie.joueur.recevoir_gain(gain)
            self.partie.luigi.solde -= gain # On pique à l'adversaire
            msg = f"🎉 Tu gagnes ! ({t_j} vs {t_l})"
            jouer_son(SON_VICTOIRE)
        else:
            gain = mise * mult_luigi
            self.partie.joueur.solde -= gain
            self.partie.luigi.recevoir_gain(gain)
            msg = f"😬 L'adversaire gagne... ({t_l} vs {t_j})"
            jouer_son(SON_DEFAITE)

        self.label_status.config(text=msg)
        self.label_solde.config(text=f"Toi: {self.partie.joueur.solde} | Adv: {self.partie.luigi.solde}")

        # Sauvegarde (même en LAN on sauvegarde ton état vs "luigi" localement pour le fun)
        sauvegarder_solde(self.partie.joueur.solde, self.partie.luigi.solde)

        # Relancer
        if self.network.is_host:
            self.root.after(4000, self.lan_host_start_round)

    # --------------------
    # Actions Joueur
    # --------------------
    def toggle_selection(self, i):
        if self.echange_effectue: return
        if i in self.selection: self.selection.remove(i)
        else: self.selection.add(i)
        self.afficher_cartes_joueur()

    def echanger(self):
        if self.echange_effectue: return
        if not self.selection:
            self.valider()
            return
        self.partie.echanger_cartes(sorted(list(self.selection)))
        self.selection.clear()
        self.echange_effectue = True
        jouer_son(SON_DISTRIB)
        self.afficher_cartes_joueur()
        self.label_status.config(text="Cartes changées. Valide pour finir.")

    def valider(self):
        self._set_buttons_state(False)
        if not self.echange_effectue: self.echange_effectue = True

        if self.mode == "solo":
            self.partie.tour_luigi()
            jouer_son(SON_DISTRIB)
            
            s_j, t_j, v_j = self.partie.joueur.main.evaluer_main()
            s_l, t_l, v_l = self.partie.luigi.main.evaluer_main()
            mult = MULTIPLICATEURS.get(t_j, 1)
            
            # Simple logique solo
            if s_j > s_l or (s_j==s_l and v_j > v_l):
                gain = self.mise * mult
                self.partie.joueur.recevoir_gain(gain)
                res = f"Gagné ! ({t_j})"
                jouer_son(SON_VICTOIRE)
            elif s_j == s_l and v_j == v_l:
                res = "Égalité"
                jouer_son(SON_EGALITE)
            else:
                gain = self.mise # Simplifié
                self.partie.luigi.recevoir_gain(gain)
                res = f"Perdu ({t_l})"
                jouer_son(SON_DEFAITE)
            
            self.reveler_cartes_adversaire()
            self.label_status.config(text=res)
            self.label_solde.config(text=f"Toi: {self.partie.joueur.solde} | Adv: {self.partie.luigi.solde}")
            sauvegarder_solde(self.partie.joueur.solde, self.partie.luigi.solde)
            self.root.after(3000, self.nouvelle_manche_solo)

        elif self.mode == "lan":
            # Envoyer ma main
            msg = {"type": "HAND", "hand_obj": self.partie.joueur.main.cartes}
            self.network.send(msg)
            self.lan_my_hand_sent = True
            
            if self.lan_opponent_hand:
                self.resolve_lan_round()
            else:
                self.label_status.config(text="En attente de l'adversaire...")

    def nouvelle_manche_solo(self):
        self.partie.distribuer()
        self.echange_effectue = False
        self.selection = set()
        self.afficher_cartes_joueur()
        self.masquer_cartes_adversaire()
        self._set_buttons_state(True)
        self.label_status.config(text="Nouvelle manche solo")

    def _set_buttons_state(self, enabled=True):
        if enabled:
            self.btn_echanger.bind("<Button-1>", lambda e: self.echanger())
            self.btn_valider.bind("<Button-1>", lambda e: self.valider())
        else:
            self.btn_echanger.bind("<Button-1>", lambda e: None)
            self.btn_valider.bind("<Button-1>", lambda e: None)

    # Solo Actions
    def augmenter_mise(self):
        if self.mise + 10 <= 30:
            self.mise += 10
            self.label_mise.config(text=f"Mise : {self.mise}")
    def diminuer_mise(self):
        if self.mise - 10 >= 10:
            self.mise -= 10
            self.label_mise.config(text=f"Mise : {self.mise}")

# ------------------------
# Menu de Démarrage
# ------------------------
class StartMenu:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Luigi - Launcher")
        self.root.geometry("600x450")
        self.root.configure(bg="#0f1720")
        
        tk.Label(root, text="POKER LUIGI", font=("Segoe UI", 30, "bold"), fg="#FFB86B", bg="#0f1720").pack(pady=(50, 10))
        tk.Label(root, text="Choisis ton mode de jeu", font=("Segoe UI", 12), fg="white", bg="#0f1720").pack(pady=(0, 40))

        btn_solo = bouton_arrondi(root, "👤 Solo vs Luigi", self.go_solo, 250, 50, "#2E8B57", "#3CB371")
        btn_solo.pack(pady=10)

        btn_host = bouton_arrondi(root, "📡 Créer Partie (Host)", self.go_host, 250, 50, "#4682B4", "#5A9BD4")
        btn_host.pack(pady=10)

        btn_join = bouton_arrondi(root, "🔗 Rejoindre (Client)", self.go_join, 250, 50, "#DAA520", "#EDC967")
        btn_join.pack(pady=10)

    def go_solo(self):
        self.root.destroy()
        launch_game("solo")

    def go_host(self):
        net = NetworkManager(is_host=True)
        ip = net.get_local_ip()
        
        # Petit popup d'attente
        wait_win = tk.Toplevel(self.root)
        wait_win.title("Attente joueur")
        wait_win.geometry("300x150")
        tk.Label(wait_win, text=f"Ton IP est : {ip}\nAttente d'un adversaire...", padx=20, pady=20).pack()
        
        def wait_thread():
            if net.start_host():
                self.root.after(0, lambda: [wait_win.destroy(), self.root.destroy(), launch_game("lan", net)])
            else:
                 self.root.after(0, lambda: [wait_win.destroy(), messagebox.showerror("Erreur", "Erreur lors du démarrage du serveur.")])

        threading.Thread(target=wait_thread, daemon=True).start()

    def go_join(self):
        ip = simpledialog.askstring("Connexion", "Entrez l'IP de l'hôte :")
        if ip:
            net = NetworkManager(is_host=False, ip=ip)
            if net.start_client():
                self.root.destroy()
                launch_game("lan", net)
            else:
                messagebox.showerror("Erreur", "Impossible de se connecter à cette IP.")

def launch_game(mode, network=None):
    r = tk.Tk()
    app = PokerAppModern(r, mode, network)
    jouer_son(SON_START)
    r.mainloop()

# ------------------------
# Lancement
# ------------------------
if __name__ == "__main__":
    root = tk.Tk()
    menu = StartMenu(root)
    root.mainloop()