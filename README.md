

#  **EvidenX (GUI)** — Digital Forensics Visualization Framework

---

##  Overview

**EvidenX (GUI)** is a **modular, web-based digital forensics visualization framework** designed to process and analyze **rooted Android data dumps** from applications such as **WhatsApp**, **Signal**, and **Instagram**.

Built on **Python (Flask)** and **modern web technologies**, it automates the **decryption**, **data parsing**, and **interactive visualization** of encrypted mobile application artifacts.
EvidenX (GUI) transforms forensic dumps into a navigable dashboard, allowing investigators to explore messages, contacts, calls, and media files through an intuitive browser interface — combining the depth of forensic extraction with the accessibility of visual analytics.

---

##  Core Vision

> Digital evidence shouldn’t just be extracted — it should be **experienced**.
> EvidenX (GUI) reimagines forensic reporting through interactive exploration, bridging the gap between **technical data** and **human understanding**.

---

##  Key Capabilities

* **Rooted Android Compatibility** — Operates directly on data acquired from rooted Android devices.
* **Multi-App Integration** — Unified web launcher for WhatsApp, Signal, and Instagram extractors.
* **No-Passphrase Decryption** — Retrieves keys directly from Android Keystore for lawful decryption.
* **Dynamic Schema Handling** — Auto-detects evolving app database formats and adjusts accordingly.
* **Cross-Linked Visualization** — Displays decrypted data across multiple views (chats, media, calls).
* **Dual Export System** — JSON for structured analysis; HTML reports for human-readable case files.
* **Real-Time Logging** — Integrated log display with event tracking for transparency.

---

##  System Architecture

```
EvidenX(GUI)/
│
├── main_launcher.py           # Central Flask web launcher
├── launcher.html              # Unified control interface
│
├── WhatsApp/
│   ├── app.py
│   ├── index.html / style.css / script.js
│   ├── setup_dependencies.py / requirements.txt
│
├── Signal/
│   ├── app.py / new.py
│   ├── index.html / style.css / script.js
│   ├── setup_dependencies.py / requirements.txt
│
└── Instagram/
    ├── app.py / Instagram_Extractor.py / Module1.py / Module2.py
    ├── setup_dependencies.py / requirements.txt
```

Each extractor runs as an **independent Flask microservice**, ensuring modular isolation, parallel scalability, and fault-tolerant execution.
The `main_launcher.py` serves as the **entry point**, providing a central dashboard that orchestrates all extractors.

---

##  Technology Stack

| Layer             | Components                                                       |
| ----------------- | ---------------------------------------------------------------- |
| **Backend**       | Python 3.x · Flask · SQLite3 · Cryptography (AES-GCM) · PyZipper |
| **Frontend**      | HTML5 · CSS3 · JavaScript (ES6)                                  |
| **Styling**       | Tailored dark forensic theme using Orbitron & Fira Code fonts    |
| **Data Layer**    | Parsed SQLite3 dumps normalized into JSON schemas                |
| **Visualization** | Flask-rendered HTML tables, media previews, and timeline graphs  |

---

##  Module Overview

###  **WhatsApp Extractor**

* Decrypts `msgstore.db.crypt14/15` databases extracted from rooted devices.
* Parses chat logs, group structures, calls, and media attachments.
* Generates:

  * Structured JSON exports
  * Interactive HTML dashboards
* Provides keyword-based filtering and chronological browsing.

###  **Signal Extractor**

* Retrieves AES-GCM encryption keys from Android Keystore.
* Decrypts SQLCipher-encrypted `signal.db` and reconstructs message histories, calls, and group structures.
* Visualizes contact networks and message timelines with in-browser filtering.

###  **Instagram Extractor**

* Scans `/data/data/com.instagram.android/` for session IDs, cached user data, and linked profiles.
* Merges outputs from dual modules (V5 + V7) for a consolidated evidence report.
* Displays discovered accounts, login sessions, and user metadata interactively.

---

##  Data Requirements

EvidenX (GUI) expects the following **rooted Android filesystem data** for accurate processing:

| Application   | Required Directories / Files                                               |
| ------------- | -------------------------------------------------------------------------- |
| **WhatsApp**  | `/data/data/com.whatsapp/`, `/data/system/users/0/keystore/`               |
| **Signal**    | `/data/data/org.thoughtcrime.securesms/`, `/data/system/users/0/keystore/` |
| **Instagram** | `/data/data/com.instagram.android/`                                        |

All data should be extracted in a **read-only, bit-level format** using standard forensic acquisition tools.

---

##  Execution Guide

###  Install Dependencies

```bash
python setup_dependencies.py
```

###  Launch EvidenX

```bash
python main_launcher.py
```

###  Access Web Dashboard

Open the URL shown in your terminal, typically:
👉 `http://127.0.0.1:5000/`

Use the **launcher interface** to start extraction modules for WhatsApp, Signal, or Instagram.

---

##  Output Structure

```
EvidenX_Output/
│
├── WhatsApp/
│   ├── whatsapp_master_data.json
│   ├── report_whatsapp.html
│
├── Signal/
│   ├── master.json
│   ├── report_signal.html
│
└── Instagram/
    ├── master.json
    ├── report_instagram.html
```

Each HTML report mirrors the data hierarchy with:

* Search and filter functions
* Collapsible chat and media sections
* Timeline-based navigation
* Downloadable evidence reports

---

## 💻 User Interface

The web UI adopts a **forensic-grade dark mode** optimized for prolonged analysis:

* **Modular Dashboard:** One-click app launcher.
* **Real-Time Progress Indicators:** Animated decryption visualizers.
* **Responsive Layout:** Fully browser-agnostic (Edge, Chrome, Firefox).
* **Interactive Filtering:** Keyword, date, or contact-based filtering.

Screenshot example :<img width="1900" height="968" alt="Screenshot 2025-10-10 172820" src="https://github.com/user-attachments/assets/baca2a60-e2d1-4805-9d56-ee3811039f7f" />


---

## 🧩 Logging & Integrity

Every extraction operation is logged in detail:

```
logs/
├── evidenx_gui.log
└── <module_name>_session.log
```

Each log file contains:

* Module initiation time
* Database discovery path
* Key recovery status
* Total records parsed
* JSON and HTML export validation hashes

All exported data is verified with **SHA-256 integrity hashes** to preserve chain-of-custody fidelity.

---

## 🔒 Forensic Compliance

* **Read-Only Data Handling:** Original dumps remain unmodified.
* **Temporary File Control:** Decrypted intermediates securely wiped post-session.
* **UTC Time Normalization:** Ensures global timestamp consistency.
* **Evidence Correlation:** Supports cross-referencing between apps.

---

## 🧪 Validation

Tested on:

* Android versions **9–14**
* WhatsApp v2.23+
* Signal SQLCipher DB v7–v8
* Instagram app data schema v340+
  Under both **logical** and **full data partition** extractions.

---

## 🧭 Roadmap

* Unified multi-app timeline builder
* Case-based dashboard with cross-source evidence correlation
* Export to PDF/CSV formats
* Integration with EvidenX (CLI) for hybrid workflows
* Multi-user case management system for forensic teams

---

## 🧾 License

Distributed under the **MIT License** — for lawful forensic research, digital investigations, and academic use.

---

## ⚡ **EvidenX (GUI)** — *Decrypt • Visualize • Investigate*

> “Turning encrypted data into visual truth.”

---



