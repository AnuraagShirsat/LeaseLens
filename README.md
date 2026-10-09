# LeaseLens

LeaseLens helps tenants in Karnataka, India understand a rental agreement before they sign it. It runs on your own computer, using the open-weights Gemma 4 model through Ollama. Nothing is uploaded anywhere.

> **LeaseLens is not legal advice.** It is a reading aid. It may make mistakes. For decisions that matter, please talk to a qualified lawyer.

Built for Hacktoberfest Hack Day Bengaluru '26 (IEEE CIS, Ramaiah Institute of Technology, MLH), Track PS01: Multimodal Community Intelligence.

## What it does

1. **Clause-level evidence and risk scoring:** reads each clause, quotes the exact words, and flags clauses you may want to ask about, with a risk level.
2. **Deposit recovery simulator:** lets you try out possible deductions and see how much deposit you may get back.
3. **Verified Karnataka rules knowledge base:** a small, checked list of rules the app is allowed to mention.
4. **Clause negotiator with human review:** drafts polite questions or change requests that you read and edit before using.
5. **Move-in evidence vault:** stores your move-in photos and notes on your own device.
6. **Completeness and contradiction checker:** points out things that seem missing, and numbers that do not match across the agreement.

## Why Gemma 4, and why local

- **Gemma 4** (`gemma4:e4b`) has open weights under the Apache 2.0 licence. It can read both text and images, so it can work with photos of agreement pages, even tilted ones.
- **Local means private.** A rental agreement contains names, addresses and money details. Running the model on your own computer means your documents never leave it.

## How it works

1. You upload the agreement as a PDF or as photos of the pages (or choose the demo data).
2. PyMuPDF and Pillow turn the pages into images.
3. Gemma 4 reads the pages and extracts the clauses and key terms (rent, deposit, notice period and so on).
4. Gemma 4 compares each clause with the rules in `kb/karnataka_rules.json` and writes a finding with a quote, a risk level and a question you may want to ask.
5. Code checks every finding: any rule ID that is not in the knowledge base is deleted, and quotes are checked against the agreement text.
6. The completeness checker looks for missing items and conflicting numbers.
7. The app shows the results. You can run the deposit simulator, review negotiation drafts, or export a summary with fpdf2.

## How to run it on Windows

You need about a few GB of free disk space for the model, and a computer that can run it.

1. Install **Python 3.11 or newer** from python.org. Tick **"Add python.exe to PATH"** during installation.
2. Install **Ollama** from ollama.com and open the app.
3. Download the model. In PowerShell:
```
   ollama pull gemma4:e4b
```
4. Get the code:
```
   git clone <https://github.com/AnuraagShirsat/LeaseLens> C:\hack\leaselens
   cd C:\hack\leaselens
```
5. Create and activate a virtual environment:
```
   python -m venv .venv
   .venv\Scripts\activate
```
   If PowerShell blocks this, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and try again. You should see `(.venv)` at the start of the line.
6. Install the libraries:
```
   pip install -r requirements.txt
```
7. Start the app:
```
   streamlit run app.py
```
   Your browser should open the app.

**No agreement to try?** Choose the **"Use demo data"** option in the app. It uses a fake agreement, so you can see how everything works.

## Knowledge base

The file `kb/karnataka_rules.json` holds the only rules the app may mention.

- **How it is built:** each rule is typed in by a person from an official source (such as the Karnataka Rent Act 1999 or the Transfer of Property Act 1882) and carries the source name, link, section, a short plain-English summary and the date it was checked.
- **Rule types:**
  - `legal_requirement`: something the official text says.
  - `contract_guidance`: official text that depends on what the agreement says.
  - `best_practice`: team guidance. It is clearly labelled, is not a legal source, and must never be read as law.
- **Citations are checked in code.** The AI can only cite a rule ID that exists in this file. Any other citation is deleted automatically.
- **Format check:** run `python kb/validate_kb.py`. It checks that fields are filled in and correctly formatted. It checks the format, not whether a rule is true.
- **How to add a rule:**
  1. Copy text from an official source and read it carefully.
  2. Add a new block to the `rules` list in `kb/karnataka_rules.json` with a new `rule_id`, and remember the comma between blocks.
  3. Type the `date_checked` yourself after comparing with the official page.
  4. Run `python kb/validate_kb.py` until it shows 0 problems.

## Evaluation

We made four fictional test agreements with known planted issues (a vague deduction clause, a deposit amount that does not match, a long lock-in with a long notice period, and a missing annexure). The script `eval/run_eval.py` runs LeaseLens on each and reports planted issues found, whether quotes appear in the agreement text, whether citations exist in the knowledge base, extra high-risk findings, and time taken.

[PASTE RESULTS TABLE]

Run it yourself with `python eval/run_eval.py`. With only four small cases, these results show how the tool behaved on our tests. They do not prove it will work on every agreement.

## Limitations and responsible use

- **Not legal advice.** The app uses words like "may" and "you may want to ask". Something being missing is not the same as it being illegal, and something being unfair is not the same as it being unlawful.
- **It can misread poor photos.** Blurry, tilted or dark pages may be read wrongly. Always check quotes against your own copy.
- **The knowledge base is small and not complete.** It does not cover every Karnataka law. Some areas, such as stamp duty and the Registration Act 1908, are not covered yet. There is no verified rule on security deposits, so the deposit guidance is labelled best practice.
- **The Karnataka Rent Act may not apply to every rental.** It depends on things like the area, rent amount, age of the building and how the property is used.
- **English agreements only.**
- **The AI can still make mistakes**, even with the checks in code.
- Only fake agreements are included in this repository.

## Privacy

LeaseLens runs on your computer. Nothing is uploaded, and no online service is used. Your move-in evidence vault is stored on your device in the `vault_data/` folder.

## Team

- Member 1: [Anuraag Shirsat], AI core and integration
- Member 2: [Ivan Byju], app and screens
- Member 3: [Kartik Kala], knowledge base, evaluation, documentation

## License

Apache License 2.0. See the [LICENSE](LICENSE) file.
