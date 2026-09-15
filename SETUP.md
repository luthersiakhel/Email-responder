# Email Autoresponder — Setup

## 1. Naklonuj repo

```bash
git clone https://github.com/luthersiakhel/Email-responder.git
cd Email-responder
```

## 2. Python prostředí

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Gmail API credentials

1. Jdi na https://console.cloud.google.com/
2. Vytvoř nový projekt (nebo vyber existující)
3. Zapni **Gmail API**: APIs & Services → Enable APIs → hledej "Gmail API" → Enable
4. Vytvoř OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
   - Stáhni JSON a ulož jako `credentials.json` do složky projektu
5. Nastav OAuth consent screen:
   - User type: **Internal** (pro firemní Google Workspace)
   - Přidej scopes: `gmail.readonly`, `gmail.modify`, `gmail.compose`

## 4. Claude CLI

Autoresponder používá Claude CLI pro klasifikaci emailů. Nainstaluj ho:

```bash
npm install -g @anthropic-ai/claude-code
```

Při prvním spuštění se přihlásíš do Anthropic účtu.

## 5. Spuštění

```bash
source venv/bin/activate

# Dry run — uvidíš co by udělal, bez vytváření draftů
python main.py --dry-run

# Jednorazové zpracování
python main.py
```

Při prvním spuštění se otevře prohlížeč pro Gmail autorizaci. Token se uloží do `token.json`.

## 6. Úprava odpovědí

Uprav `Claude_KB.md` — přidej/odeber kategorie, regiony a šablony odpovědí.
Změny se projeví okamžitě (soubor se načítá při každém zpracování).

Struktura KB:
```
# Region (EU, CZ, UK, ...)
## Téma (Laptop Returns, PC registration, ...)
### Konkrétní situace
***Keywords:*** klíčová slova pro matching
***Answer:*** šablona odpovědi
```

## Struktura projektu

```
Email-responder/
├── main.py                  # Hlavní skript — CLI
├── gmail_client.py          # Gmail API (čtení, drafty, labely, přílohy)
├── classifier.py            # Claude AI klasifikace + generování odpovědí
├── config.py                # Konfigurace
├── Claude_KB.md             # Knowledge base — canned responses
├── Expense Claim Form.pdf   # Příloha pro externí odesílatele (box reimbursement)
├── Shipping Instructions/   # PDF s instrukcemi pro jednotlivé regiony
├── requirements.txt         # Python závislosti
├── credentials.json         # Gmail OAuth (stáhneš z Google Console, NEcommituj)
└── token.json               # Gmail token (vygeneruje se automaticky, NEcommituj)
```

## Jak to funguje

1. Skript načte emaily s labelem `LAPTOP returns` bez labelu `AutoResponder/Processed`
2. Přeskočí automatické notifikace (DHL, ServiceNow, SLA warnings, ...)
3. Každý email pošle Claude CLI s knowledge base (`Claude_KB.md`)
4. Claude klasifikuje email, vybere nejlepší canned response a vygeneruje draft
5. Draft se uloží v Gmailu — ty ho zkontoluješ a pošleš
6. Pokud odesílatel zmíní, že nemá krabici a je to externí osoba (ne @redhat.com), přiloží se `Expense Claim Form.pdf`
7. Email se označí labelem `AutoResponder/Processed`

## Git workflow

```bash
# Stáhni nejnovější verzi
git pull

# Po úpravách
git add -A
git commit -m "popis změny"
git push
```
