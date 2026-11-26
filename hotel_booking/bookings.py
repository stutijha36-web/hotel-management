from core import (
    abort, app, clean, date, flash,
    g, need, num, q, redirect,
    render_template, request, run, scope, table,
    url_for)
from booking import owned, my_booking, set_status, log

@app.route("/my-bookings")
@need("customer")
def my_bookings():
    rows = q("select b.*, h.name hotel, r.room_no, (select 1 from reviews v where v.booking_id=b.id) reviewed from bookings b join rooms r on r.id=b.room_id join hotels h on h.id=r.hotel_id where b.user_id=? order by b.id desc", (g.user["id"],))
    return render_template("bookings.html", rows=rows, today=date.today().isoformat())

@app.route("/cancel/<int:bid>", methods=["POST"])
@need("customer")
def cancel(bid):
    b = owned(bid)
    if b["status"] in ("Pending", "Confirmed") and b["check_in"] > date.today().isoformat():
        set_status(bid, "Cancelled", "Cancelled by customer")
        run("update payments set status='Refunded' where booking_id=?", (bid,)); flash("Booking cancelled." + (" Payment marked refunded." if b["status"] == "Confirmed" else ""))
    else: flash("This booking can no longer be cancelled.")
    return redirect("/my-bookings")

@app.route("/review/<int:bid>", methods=["POST"])
@need("customer")
def review(bid):
    b, rating = owned(bid), num(request.form.get("rating"), 0, int)
    if b["status"] != "Checked-Out" or not 1 <= rating <= 5 or q("select 1 from reviews where booking_id=?", (bid,), one=True): flash("Cannot review this booking.")
    else: run("insert into reviews(booking_id,user_id,room_id,rating,comment) values(?,?,?,?,?)", (bid, g.user["id"], b["room_id"], rating, clean(request.form.get("comment")))); flash("Thanks for your review!")
    return redirect("/my-bookings")

NEXT = {"Confirmed": ["Checked-In", "Cancelled"], "Pending": ["Cancelled"], "Checked-In": ["Checked-Out"]}

@app.route("/admin/bookings")
@need("admin", "manager")
def bookings_admin():
    s, a = scope(); st = request.args.get("status", "")
    rows = [dict(cells=[x["code"], x["customer"], f'{x["hotel"]} #{x["room_no"]}', f'{x["check_in"]} to {x["check_out"]}', x["total"], x["status"], x["paid"] or "-"],
                 actions=[(n, url_for("set_booking", bid=x["id"], status=n), "post") for n in NEXT.get(x["status"], [])]) for x in
            q("select b.*, u.name customer, h.name hotel, r.room_no, (select status from payments p where p.booking_id=b.id) paid from bookings b join users u on u.id=b.user_id join rooms r on r.id=b.room_id join hotels h on h.id=r.hotel_id where (?='' or b.status=?)" + s + " order by b.id desc", [st, st] + a)]
    return table("Bookings", ["ID", "Customer", "Room", "Stay", "Total", "Status", "Payment"], rows)

@app.route("/admin/bookings/<int:bid>/<status>", methods=["POST"])
@need("admin", "manager")
def set_booking(bid, status):
    b, s = my_booking(bid), None
    if g.user["role"] == "manager" and b["hotel_id"] != g.user["hotel_id"]: abort(403)
    if status in NEXT.get(b["status"], []):
        set_status(bid, status, f"Updated by {g.user['role']}")
        if status == "Cancelled": run("update payments set status='Refunded' where booking_id=?", (bid,))
    else: flash("Invalid status change.")
    return redirect(url_for("bookings_admin"))
