from core import extract

pdf_path = r"C:\Projects\GitHub\LeaseLens\eval\cases\case1\case1.pdf"

print("Loading model (first call is slow)...", flush=True)
result = extract.extract_agreement_from_pdf(pdf_path)

print(f"\nDone. {len(result.clauses)} clauses, {result.page_count} pages.")
print(f"Rent: {result.key_terms.monthly_rent}")
print(f"Deposit: {result.key_terms.security_deposit}")