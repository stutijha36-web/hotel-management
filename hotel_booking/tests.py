import os, tempfile
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
from datetime import date, timedelta as td
import app as A
A.init_db(); A.app.config["TESTING"] = True
import sqlite3
def Q(s): c = sqlite3.connect(A.DB); r = c.execute(s).fetchall(); c.close(); return r[0] if len(r) == 1 and len(s) else r
D = lambda n: (date.today() + td(days=n)).isoformat()
def client(email, pw):
    c = A.app.test_client(); r = c.post("/login", data=dict(email=email, password=pw)); assert r.status_code == 302; return c
def book(c, rid, a, b, guests=1):
    return c.post(f"/book/{rid}", data=dict(check_in=D(a), check_out=D(b), guests=guests, full_name="Test User", phone="9876543210"))
g1 = client("guest@hotel.com", "Guest@123")
r = A.app.test_client().post("/register", data=dict(name="Second", email="two@x.com", phone="9111111111", password="Passw0rd1")); assert r.status_code == 302
g2 = client("two@x.com", "Passw0rd1")
assert A.app.test_client().post("/register", data=dict(name="X", email="bad", phone="1", password="a")).status_code == 200
r = book(g1, 1, 5, 8); assert "/pay/1" in r.location; assert Q("select total from bookings where id=1")[0] == 2500*3*1.17
assert "just booked" in g2.get(book(g2, 1, 6, 9).location, follow_redirects=True).get_data(as_text=True)
assert "/pay/" in book(g2, 1, 8, 10).location
assert "/pay/" in book(g2, 2, 6, 9).location
assert "allows" in g1.get(book(g1, 1, 20, 22, guests=5).location, follow_redirects=True).get_data(as_text=True)
g1.post("/pay/1/confirm"); assert Q("select status from bookings where id=1")[0] == "Confirmed" and Q("select count(*) from payments")[0] == 1
assert g2.get("/receipt/1").status_code == 403
g1.post("/cancel/1"); assert Q("select status from bookings where id=1")[0] == "Cancelled" and Q("select status from payments")[0] == "Refunded"
assert "/pay/" in book(g2, 1, 6, 7).location
m = client("manager@hotel.com", "Manager@123"); assert m.get("/admin").status_code == 200 and m.get("/admin/hotels").status_code == 403
g2.post("/pay/2/confirm"); m.post("/admin/bookings/2/Checked-In"); m.post("/admin/bookings/2/Checked-Out"); assert Q("select status from bookings where id=2")[0] == "Checked-Out"
ad = client("admin@hotel.com", "Admin@123")
for u in ["/admin", "/admin/hotels", "/admin/rooms", "/admin/bookings", "/admin/reports?type=monthly", "/admin/reports?type=occupancy", "/admin/reports?type=customers", "/admin/reports?type=daily&fmt=csv", "/admin/reports?type=monthly&fmt=pdf", "/?city=delhi&check_in=%s&check_out=%s" % (D(1), D(2)), "/room/1", "/profile", "/forgot"]:
    assert ad.get(u).status_code == 200, u
print("ALL TESTS PASSED")
