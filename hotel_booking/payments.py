from core import (
    RZP_KEY, RZP_SECRET, app, date, flash,
    hashlib, hmac, need, q, redirect,
    render_template, request, run, secrets, session,
    url_for)
from booking import owned, set_status
from search import is_free

@app.route("/pay/<int:bid>")
@need("customer")
def pay(bid):
    b = owned(bid)
    if b["status"] != "Pending": return redirect(url_for("receipt", bid=bid))
    order = None
    if RZP_KEY:
        import razorpay
        order = razorpay.Client(auth=(RZP_KEY, RZP_SECRET)).order.create({"amount": int(b["total"] * 100), "currency": "INR", "receipt": b["code"]})
        session[f"ord{bid}"] = order["id"]
    return render_template("pay.html", b=b, order=order, key=RZP_KEY)

@app.route("/pay/<int:bid>/confirm", methods=["POST"])
@need("customer")
def pay_confirm(bid):
    b, f = owned(bid), request.form
    if b["status"] != "Pending": return redirect(url_for("receipt", bid=bid))
    if RZP_KEY:
        oid, pid = session.get(f"ord{bid}"), f.get("razorpay_payment_id", "")
        sig = hmac.new(RZP_SECRET.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
        if f.get("razorpay_order_id") != oid or not hmac.compare_digest(sig, f.get("razorpay_signature", "")): flash("Payment verification failed."); return redirect(url_for("pay", bid=bid))
        method, txn = "Razorpay (test)", pid
    else: method, txn = "Simulated test payment", "TEST" + secrets.token_hex(5).upper()
    ci, co = date.fromisoformat(b["check_in"]), date.fromisoformat(b["check_out"])
    if not is_free(b["room_id"], ci, co, skip=bid): set_status(bid, "Cancelled", "Room taken before payment"); flash("Room is no longer available."); return redirect("/my-bookings")
    run("insert into payments(booking_id,amount,method,txn_id,receipt_no) values(?,?,?,?,?)", (bid, b["total"], method, txn, "RCPT-" + b["code"]))
    set_status(bid, "Confirmed", "Payment " + txn); flash("Payment successful. Booking confirmed!"); return redirect(url_for("receipt", bid=bid))

@app.route("/receipt/<int:bid>")
@need()
def receipt(bid):
    b = owned(bid); p = q("select * from payments where booking_id=?", (bid,), one=True)
    return render_template("receipt.html", b=b, p=p, c=q("select * from customers where id=?", (b["customer_id"],), one=True))
