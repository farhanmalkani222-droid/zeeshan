"""Tally Prime / ERP 9 XML import for the posted vouchers (Credit Note / Debit Note, Against Ref bill-to-bill).
Ledger names are configurable; they must exist in Tally. Test on a dummy company first."""
from xml.sax.saxutils import escape

LEDGERS = {"sales_adj": "Sales Adjustment - Short/Rate", "purchase_adj": "Purchase Adjustment - Short/Rate",
           "output_gst": "Output GST", "input_gst": "Input GST"}


def _d(iso):
    return iso.replace("-", "")


def _entry(ledger, amount, debit, bill=None):
    # Tally: debit entries are ISDEEMEDPOSITIVE=Yes with a negative amount; credit entries positive.
    amt = f"{-amount if debit else amount:.2f}"
    alloc = (f"<BILLALLOCATIONS.LIST><NAME>{escape(bill)}</NAME><BILLTYPE>Agst Ref</BILLTYPE><AMOUNT>{amt}</AMOUNT></BILLALLOCATIONS.LIST>"
             if bill else "")
    return (f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{escape(ledger)}</LEDGERNAME><ISDEEMEDPOSITIVE>{'Yes' if debit else 'No'}</ISDEEMEDPOSITIVE>"
            f"<AMOUNT>{amt}</AMOUNT>{alloc}</ALLLEDGERENTRIES.LIST>")


def vouchers(c, company=None, ledgers=None, include_exported=False):
    L = {**LEDGERS, **(ledgers or {})}
    out = []
    for n in c.execute("""SELECT n.*, m.name ledger, b.ref_no bill_ref FROM notes n JOIN masters m ON m.id=n.master_id
                          JOIN bills b ON b.id=n.bill_id WHERE n.note_type IN ('CN-to-party','DN-to-mill') AND (n.exported=0 OR ?) ORDER BY n.note_date, n.id""", (int(include_exported),)):
        total = round(n["amount"] + n["gst"], 2)
        if n["note_type"] == "CN-to-party":    # Dr Sales adj (+GST), Cr Party against sale bill
            vt = "Credit Note"
            ents = _entry(L["sales_adj"], n["amount"], True) + (_entry(L["output_gst"], n["gst"], True) if n["gst"] else "") \
                + _entry(n["ledger"], total, False, n["bill_ref"])
        else:                                   # Dr Mill against purchase bill, Cr Purchase adj (+GST)
            vt = "Debit Note"
            ents = _entry(n["ledger"], total, True, n["bill_ref"]) + _entry(L["purchase_adj"], n["amount"], False) \
                + (_entry(L["input_gst"], n["gst"], False) if n["gst"] else "")
        out.append(f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="{vt}" ACTION="Create"><DATE>{_d(n["note_date"])}</DATE>'
                   f'<VOUCHERTYPENAME>{vt}</VOUCHERTYPENAME><VOUCHERNUMBER>{escape(n["tally_voucher_no"])}</VOUCHERNUMBER>'
                   f'<REFERENCE>{escape(n["note_no"])}</REFERENCE><NARRATION>{escape(n["narration"] or "")}</NARRATION>{ents}</VOUCHER></TALLYMESSAGE>')
    co = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape(company)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company else ""
    return ('<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC>'
            f'<REPORTNAME>Vouchers</REPORTNAME>{co}</REQUESTDESC><REQUESTDATA>{"".join(out)}</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>')


def mark_exported(c):
    c.execute("UPDATE notes SET exported=1 WHERE note_type IN ('CN-to-party','DN-to-mill')")
