# HAWA PRO – Debit & Credit Note module

Implements the *Structural Build Plan* (Oct 2, 2026): party debit note → credit note to party **and** paired debit note on the mill, bill-to-bill, date-ordered, with reconciliation and Tally import XML. Pure Python 3 stdlib + SQLite (`HAWAPRO_DB`, default `./hawapro.db`).

## Daily flow
```
python3 -m hawapro master-add mill Craftech --alias "craftech paper"      # masters (aliases resolve odd spellings)
python3 -m hawapro master-add party "Rajesh Traders" --alias RT
python3 -m hawapro bill-add HGH/P/0901 purchase 2026-09-05 Craftech 12400 22
python3 -m hawapro bill-add HGH/S/1042 sale 2026-09-12 "Rajesh Traders" 12400 24.5 --linked HGH/P/0901   # sale bill traces to its purchase bill
python3 -m hawapro stage RT HGH/S/1042 DN-5567 2026-09-18 short-qty --short-qty 180 --accepted-rate 23 --channel whatsapp --file DN-5567.pdf
python3 -m hawapro import-csv notes.csv      # or bulk: party,bill,note_no,date,reason,short_qty,qty,accepted_rate,amount,gst,mill,channel,file
python3 -m hawapro queue                     # sorted by the note's own date, flags shown
python3 -m hawapro verify-all                # sign off clean notes; flagged ones stay held
python3 -m hawapro post --dry-run            # preview, then without --dry-run
python3 -m hawapro post --xml notes.xml --company "H.G. Hawa & Co."   # Tally import file (new vouchers only)
python3 -m hawapro mill-cn <mill-DN-id> MCN-77 2026-10-05 4140        # mill's credit note comes back later
python3 -m hawapro report day-register|bill-outstanding|pending-mill-cn|linkage|month-gap|exceptions [--csv]
python3 -m hawapro demo                      # sample data with the plan's mills
```

## Intake, web screen, register load (plan Phases 3-5)
```
python3 -m hawapro bills-import bills.csv --create-masters   # ref_no,side,date,party_or_mill,quantity_kg,rate[,value,gst_rate,open_balance,linked_ref,gst_no,location]; idempotent
python3 -m hawapro intake ./incoming --channel whatsapp      # folder or single file of debit-note .pdf/.txt -> staging queue (idempotent by file hash)
python3 -m hawapro verify-all --min-confidence 0.7           # auto-sign-off only notes the extractor was sure of
python3 -m hawapro set-ledger sales_adj "Your Sales Adj Ledger"   # also purchase_adj, output_gst, input_gst
python3 -m hawapro serve [--port 8765]                       # web: queue/verify/reject/edit, upload, post preview + post, reports, mill credit notes, Tally XML download
```
- **Extraction** is register-guided: it looks for your known party names/aliases, known sale-bill refs and mill names in the text, then labelled fields (note no., date in `dd-mm-yyyy`/`dd Mon yyyy`/ISO, short qty, accepted rate, amount, GST). PDFs need `pdftotext` (poppler-utils). If `ANTHROPIC_API_KEY` is set, a Claude pass (`HAWAPRO_LLM_MODEL`, default Haiku) runs first and regex fills gaps. Whatever is extracted still goes through every validation check and your sign-off; unreadable files are logged as failed (see Intake page), never posted.
- **Web screen** binds to `127.0.0.1`; set `HAWAPRO_PASSWORD` (HTTP Basic) before exposing it on a network and put it behind HTTPS. Writes are CSRF-protected. `HAWAPRO_COMPANY` sets the Tally company in the XML.
- Mail/WhatsApp *fetching* is not automated: save attachments into a folder and run `intake` (or upload on the Intake page).

## What is enforced
- **Validation (hold → exceptions queue):** bill exists/open, amount ≤ open balance (also against running balance inside a batch), claim recomputed (`short qty × rate` or `(billed − accepted rate) × qty`, ±₹1), duplicate note rejected (alias-aware), GST recomputed (rate per bill, default 18%), closed-period (`close-period YYYY-MM-DD`), name must resolve to one master, mill must match the bill's trace.
- **Pairing:** a party note posts only together with its mill debit (same date, linked ids). A sale bill with no linked purchase bill blocks (`NO_MILL_LINK`). The mill debit defaults to the same taxable amount; override with `--mill-amount`.
- **Sequencing:** queue and posting run ascending by note date across all parties/mills; Tally voucher numbers (`CN/n`, `DN/n`) are therefore chronological.
- **Reconciliation:** mill debits stay *pending* until its credit note is recorded (month-gap view treats this as timing); *mismatch* if amounts differ; *overdue* after 60 days.

## Assumptions to confirm
- Bill `value` and note `amount` are **taxable**; GST is computed on top.
- Tally ledger names (`Sales Adjustment - Short/Rate`, `Purchase Adjustment - Short/Rate`, `Output GST`, `Input GST`) are placeholders – edit `hawapro/tally.py:LEDGERS`. Try the XML on a dummy company first; it was validated for balance and well-formedness, not against a live Tally.
- Extraction was tested on synthetic notes only; real party layouts will need a pass of tuning (send samples). The register loads from CSV, not live from Tally, and the XML is a file you import (no live Tally connection).

Tests: `python3 -m unittest tests.test_hawapro tests.test_hawapro_intake_web`
