"""Bill reference register: the open sale / purchase bills every note attaches to (Tally 'New Ref')."""


def add_bill(c, ref_no, side, bill_date, master_id, quantity_kg, rate, value=None, gst_rate=18.0, linked_ref=None):
    value = round(quantity_kg * rate, 2) if value is None else round(value, 2)
    c.execute("""INSERT INTO bills(ref_no,side,bill_date,master_id,quantity_kg,rate,value,gst_rate,open_balance,linked_ref)
                 VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (ref_no, side, bill_date, master_id, quantity_kg, rate, value, gst_rate, value, linked_ref))


def get_bill(c, ref_no, side):
    return c.execute("SELECT * FROM bills WHERE ref_no=? AND side=?", (ref_no, side)).fetchone()


def status(bill):
    return "open" if bill["open_balance"] > 0.005 else "closed"
