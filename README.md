# 🤖 Proiectul de Conducere și Administrare a Facțiunii (PCAF)

![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?style=for-the-badge&logo=python)
![Discord.py](https://img.shields.io/badge/Discord.py-2.7+-green?style=for-the-badge&logo=discord)
![Firebase](https://img.shields.io/badge/Firebase-Realtime--DB-orange?style=for-the-badge&logo=firebase)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge&logo=opensourceinitiative)

PCAF este un bot conceput special pentru a eficientiza și a ușura administrarea unei facțiuni prin intermediul a numeroase funcționalități avansate (dezvoltat inițial pentru comunitatea GreenStone România).

---

## ✨ Funcționalități Principale

* 📊 Evidență Rapoarte: Verificarea automată a activității prin analizarea datelor introduse. Sistemul oferă o situație detaliată: afișează membrii care au finalizat raportul, calculează automat Membru Săptămânii (M.S.) și indică exact ce progres le lipsește celor care nu și-au îndeplinit obiectivele.
* ⚙️ Gestiune Membri și Automatizări: Comenzi dedicate pentru adăugarea rapidă a utilizatorilor în baza de date, incrementarea automată a zilelor petrecute în facțiune (rankup system) și monitorizarea prezenței la activitățile de tip Roleplay (RP).
* 🛡️ Securitate și Moderare Avansată: Modul de protecție anti-raid pentru securizarea serverului și sistem inteligent de filtrare chat, capabil să blocheze automat cuvinte, expresii sau fraze interzise.
* ⚖️ Sistem de Sancțiuni: Gestionare automată pentru FW (Faction Warn) și AV (Avertisment Verbal) cu logică de cumulare (2 AV = 1 FW).
* 🔒 Arhitectură Securizată: Toate cheile sensibile, token-urile și legăturile de baze de date sunt mutate complet în variabile de mediu (.env).
* 💾 Bază de Date Firebase: Integrare cu Firebase Realtime Database pentru stocarea permanentă a datelor.
* ℹ️ Logs comenzi ce se trimit la un server special: Pentru asigurarea functionalitati a botului si impiedicarea acuzatilor false.

---
## 📌 De reținut (Proiect Închis)
Acest proiect este definitiv încheiat și arhivat, ceea ce înseamnă că nu va mai primi actualizări, optimizări sau patch-uri pentru bug-uri. Botul a rămas în stadiul stabil actual, având însă câteva funcționalități care au rămas parțial incomplete:
* Lipsa logării complete pentru comenzi: În versiunea curentă, nu toate comenzile executate de utilizatori sunt trimise către sistemul de loguri.
* Modulul de audit/evenimente neterminat: Sistemul de loguri automate pentru acțiunile generale ale serverului (care ar fi trebuit să înregistreze intrările/ieșirile membrilor, schimbările de roluri sau editarea permisiunilor) a rămas incomplet implementat.

---
## 🚀 Ghid de Instalare și Configurare

Pentru a rula acest proiect pe calculatorul sau hostul tău, urmează pașii de mai jos:

### 1. Clonarea proiectului
* Comandă terminal: git clone https://github.com/rusualingabriel/pcaf.git
* Schimbare director: cd pcaf

### 2. Instalarea dependențelor
Asigură-te că ai Python 3.11 sau mai nou instalat. Rulează comanda în consolă:
* Comandă: pip install discord.py firebase-admin python-dotenv pytz

### 3. Configurarea fișierului de securitate (.env)
Editează fișierul .env cu informațile necesare:

DISCORD_TOKEN=AICI_PUI_TOKEN_UL_BOTULUI_TAU

OWNER_ID=ID_UL_TAU_DE_DISCORD

FIREBASE_URL=https://numele-bazei-tale.firebaseio.com/

GUILD_STAFF_ID=ID_UL_SERVERULUI_DE_STAFF

### 4. Credențialele Firebase
Descărcați fișierul .json cu cheia privată din consola Firebase (Project Settings -> Service Accounts), redenumiți-l în "firebase-adminsdk.json" și înlocuiți în folderul principal al botului.

### 5. Pornirea botului
* Comandă: py main.py

---

## ⚙️ Structura Bazei de Date (Important)
> ⚠️ Notă: Din motive de securitate, conexiunile directe și structura pre-generată a nodurilor din baza mea de date Firebase au fost eliminate din codul open-source publicat. Utilizatorul este obligat să își configureze manual nodurile și tabelele corespunzătoare în Firebase înainte de a rula logica de stocare.

---

## ✍️ Credite și Autor

* Creator și Dezvoltator Principal: rusualingabriel - Toate drepturile asupra arhitecturii inițiale de 7.000+ linii de cod îi aparțin.
* Proiectul este publicat ca Open-Source pentru a ajuta comunitatea, dar ștergerea creditelor sau pretinderea codului ca fiind proprietate proprie fără specificarea autorului inițial încalcă termenii.
* Întrebări: Pentru orice nelămurire sau detalii suplimentare legate de proiect, mă puteți contacta pe Discord la username-ul `devarchitect_`.

⚠️ **IMPORTANT REFORZAT** (Sistem de Siguranță):
Vă rugăm să păstrați comanda /credits, ca o formă minimă de respect pentru orele de muncă depuse.

**Notă tehnică**: Codul sursă conține sisteme integrate de verificare a integrității (măsuri de protecție). Orice tentativă de a șterge, modifica sau ascunde comanda de credite sau numele autorului va duce la oprirea automată a botului.

---

## ⚖️ Licență

Acest proiect este licențiat sub Licența MIT. Puteți modifica, distribui și folosi codul, cu condiția obligatorie de a păstra fișierul de licență și mențiunea copyright-ului original (Copyright (c) 2026 rusualingabriel) în toate copiile software-ului.
