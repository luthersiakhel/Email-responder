# Email Autoresponder — Setup

## 1. Python prostředí

```bash
cd ~/email-autoresponder
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Gmail API credentials

1. Jdi na https://console.cloud.google.com/
2. Vytvoř nový projekt (nebo vyber existující)
3. Zapni **Gmail API**: APIs & Services → Enable APIs → hledej "Gmail API" → Enable
4. Vytvoř OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Desktop app**
   - Stáhni JSON a ulož jako `credentials.json` do složky `~/email-autoresponder/`
5. Nastav OAuth consent screen:
   - User type: **Internal** (pro firemní Google Workspace)
   - Přidej scopes: `gmail.readonly`, `gmail.modify`, `gmail.compose`

## 3. Anthropic API klíč

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

Klíč získáš na https://console.anthropic.com/

## 4. Spuštění

```bash
# Prvni spuštění — otevře prohlížeč pro Gmail autorizaci
# Pak uloží token.json pro příští spuštění

# Dry run — uvidíš co by udělal, bez vytváření draftů
python main.py --dry-run

# Jednorazové zpracování
python main.py

# Kontinuální sledování (kontrola každých 60s)
python main.py --watch

# Vlastní interval (každých 5 minut)
python main.py --watch --interval 300
```

## 5. Úprava odpovědí

Uprav `knowledge_base.yaml` — přidej/odeber kategorie a šablony odpovědí.
Změny se projeví okamžitě (soubor se načítá při každém zpracování).

## Struktura projektu

```
email-autoresponder/
├── main.py              # Hlavní skript — CLI
├── gmail_client.py      # Gmail API (čtení, drafty, labely)
├── classifier.py        # Claude AI klasifikace + generování odpovědí
├── config.py            # Konfigurace
├── knowledge_base.yaml  # Kategorie a šablony odpovědí
├── requirements.txt     # Python závislosti
├── credentials.json     # Gmail OAuth (stáhneš z Google Console)
└── token.json           # Gmail token (vygeneruje se automaticky)
```

## Jak to funguje

1. Skript načte nepřečtené emaily bez labelu `AutoResponder/Processed`
2. Každý email pošle Claude API s knowledge base
3. Claude klasifikuje email do kategorie a vygeneruje odpověď
4. Odpověď se uloží jako **draft** v Gmailu — ty ho zkontoluješ a pošleš
5. Email se označí labelem `AutoResponder/Processed`

## Tipy

- Začni s `--dry-run` a zkontroluj kvalitu klasifikace
- Uprav šablony v `knowledge_base.yaml` podle reálných odpovědí
- Pro nižší náklady změň model v `config.py` na `claude-sonnet-5`
