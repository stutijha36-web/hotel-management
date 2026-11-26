from core import app, need, q, render_template, scope

@app.route("/admin")
@need("admin", "manager")
def dashboard():
    s, a = scope(); one = lambda sql, x=a: q(sql, x, one=True)[0]
    rooms = one("select count(*) from rooms r where active=1" + s)
    occ = one("select count(distinct b.room_id) from bookings b join rooms r on r.id=b.room_id where b.status='Checked-In'" + s)
    st = {"Registered customers": one("select count(*) from users where role='customer'", []), "Hotels": 1 if s else one("select count(*) from hotels", []), "Rooms": rooms,
          "Bookings": one("select count(*) from bookings b join rooms r on r.id=b.room_id where 1" + s), "Occupied rooms": occ, "Available rooms": rooms - occ,
          "Revenue (Rs)": one("select coalesce(sum(p.amount),0) from payments p join bookings b on b.id=p.booking_id join rooms r on r.id=b.room_id where p.status='Paid'" + s)}
    rec = q("select b.code, u.name, h.name, r.room_no, b.check_in, b.check_out, b.total, b.status from bookings b join users u on u.id=b.user_id join rooms r on r.id=b.room_id join hotels h on h.id=r.hotel_id where 1" + s + " order by b.id desc limit 8", a)
    return render_template("dashboard.html", st=st, rec=rec)
