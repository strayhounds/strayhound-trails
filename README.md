# 🐾 StrayHound Trails

> *Every hunt leaves a trail. This is where we keep them.*

**StrayHound Trails** is an archive of the CTF challenges the StrayHound team has hunted, kept so that anyone can walk the same trails afterwards. Each competition is organized by category, and each challenge keeps its original text and its files.

No pack required. Pick a trail and follow it.

[🌐 Website](https://strayhound.team) · [📜 CTF history](https://strayhound.team/ctf/)

---

## 🩸 What's in here

One repo. Many hunts.

- **Competitions:** every CTF we played, one folder each.
- **Categories:** inside each competition, challenges are sorted by category (crypto, forensics, web, pwn, reverse, misc...).
- **Challenges:** each challenge has its **original description** and its **challenge files**, so you can play it as it was played.

Solutions are **not** stored with the challenges. Write-ups live on our website, so the trails stay unspoiled until you want the answer.

---

## 🗺️ Competitions

| Year | Competition | Played | Result | Trails |
|------|-------------|--------|--------|--------|
| 2026 | [CSCTF 2026: Total Warfare](competitions/2026-csctf) | Nov 6-8 | 66th / 294 (Fighters) | [Enter](competitions/2026-csctf) |
| COUNTERSIGN | Crypto | 120 | [Open](crypto/countersign) |

*More hunts will be added as we go.*

---

## 📂 Layout

```
strayhound-trails/
├── README.md
├── LICENSE
└── competitions/
    └── 2026-csctf/
        ├── README.md              ← event info and challenge list
        ├── crypto/
        │   └── challenge-name/
        │       ├── README.md      ← the challenge text, as written
        │       └── files/         ← the challenge files
        ├── forensics/
        └── misc/
```

Names are lowercase, with hyphens instead of spaces.

---

## 🐺 How to play

1. Clone the repo:
   ```bash
   git clone https://github.com/strayhounds/strayhound-trails.git
   cd strayhound-trails
   ```
2. Pick a competition, then a category, then a challenge.
3. Read the challenge's `README.md`. It has the original description.
4. Grab the files from its `files/` folder and start hunting.
5. Stuck for too long? Read the write-up on [strayhound.team](https://strayhound.team) afterwards, not before.

> Some large files are stored with **Git LFS**. If a file looks tiny or broken after cloning, run `git lfs install && git lfs pull`.

---

## ⚠️ Read before you hunt

- **Offline services.** Challenges that needed a live server were hosted by the organizers and are **no longer running**. If a Docker setup was provided, it's included. If not, the challenge is marked as unavailable.
- **Untrusted files.** Some forensics and reverse challenges contain suspicious or malicious files by design. Open them in a **virtual machine**, never on your main system.
- **Ethical hacking only.** These challenges exist for learning. Use what you learn legally and responsibly.

---

## 🤝 Credits and ownership

The challenges belong to their **original authors and organizers**, who are credited in each competition's README. StrayHound did not create them and shares them here for learning and archival purposes. If you are an organizer or author and want something credited differently or removed, open an issue and we will act on it.

Our own write-ups, notes and structure are ours. See the license below.

---

## 📜 License

The repository structure, documentation and StrayHound-written content are released under the **[LICENSE](LICENSE)** in this repo. The challenge files and texts remain the property of their original creators and are **not** covered by this license.

---

## 🌑 About StrayHound

A pack of strays hunting flags in the dark. Still learning, still fighting, still hungry.

*We don't wait for the trail. We follow it.*