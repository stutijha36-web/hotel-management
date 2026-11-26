from core import (
    abort, app, clean, date, db,
    flash, g, need, num, q,
    re, redirect, request, secrets, session,
    url_for)
from search import is_free, quote, get_room, parse_dates
from auth import save_customer

def log(bid, status, note=""): db().execute("insert into booking_history(booking_id,status,note,changed_by) values(?,?,?,?)", (bid, status, note, session.get("uid")))

def set_status(bid, status, note=""): db().execute("update bookings set status=? where id=?", (status, bid)); log(bid, status, note); db().commit()

@app.route("/book/<int:rid>", methods=["POST"])
@need("customer")
def book(rid):
    r, f = get_room(rid), request.form; d = parse_dates(f); guests = num(f.get("guests"), 0, int); name, phone = clean(f.get("full_name")), clean(f.get("phone"))
    err = []
    if not d: err.append("Invalid dates.")
    if not 1 <= guests <= r["capacity"]: err.append(f"This room allows 1-{r['capacity']} guests.")
    if len(name) < 2 or not re.fullmatch(r"\+?\d{10,13}", phone): err.append("Enter valid name and phone.")
    if err:
        for e in err: flash(e)
        return redirect(url_for("room", rid=rid, **{k: f.get(k, "") for k in ("check_in", "check_out", "guests")}))
    cid, c = save_customer(g.user["id"], name, phone, clean(f.get("address"))), db()
    c.execute("BEGIN IMMEDIATE")
    try:
        if not is_free(rid, *d): c.rollback(); flash("Sorry, this room was just booked for those dates."); return redirect(url_for("search"))
        qt = quote(r, *d); code = "BK" + date.today().strftime("%y%m%d") + secrets.token_hex(3).upper()
        bid = c.execute("insert into bookings(code,user_id,customer_id,room_id,check_in,check_out,guests,nights,base_amount,tax,service_charge,total) values(?,?,?,?,?,?,?,?,?,?,?,?)",
            (code, g.user["id"], cid, rid, d[0].isoformat(), d[1].isoformat(), guests, qt["nights"], qt["base"], qt["tax"], qt["svc"], qt["total"])).lastrowid
        log(bid, "Pending", "Booking created"); c.commit()
    except Exception: c.rollback(); raise
    return redirect(url_for("pay", bid=bid))

def my_booking(bid):
    return q("select b.*, r.room_no, r.hotel_id, h.name hotel, h.city, t.name type from bookings b join rooms r on r.id=b.room_id join hotels h on h.id=r.hotel_id join room_types t on t.id=r.type_id where b.id=?", (bid,), one=True) or abort(404)

def owned(bid):
    b = my_booking(bid)
    if b["user_id"] != g.user["id"] and not (g.user["role"] == "admin" or (g.user["role"] == "manager" and g.user["hotel_id"] == b["hotel_id"])): abort(403)
    return b
