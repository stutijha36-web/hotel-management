import os, re, csv, io, hmac, hashlib, secrets, sqlite3

from datetime import date, datetime, timedelta

from functools import wraps

from flask import Flask, g, session, request, redirect, url_for, flash, render_template, abort, Response

from werkzeug.security import generate_password_hash as gph, check_password_hash as cph

app = Flask(__name__)

app.config.update(SECRET_KEY=os.getenv("SECRET_KEY", "dev-change-me"), SESSION_COOKIE_SAMESITE="Lax", MAX_CONTENT_LENGTH=4 * 1024 * 1024)

DB = os.getenv("DB_PATH", os.path.join(app.root_path, "hotel.db"))

UPLOAD = os.path.join(app.root_path, "static", "uploads")

RZP_KEY, RZP_SECRET = os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET")

TAX, SERVICE = 0.12, 0.05

HOLD = "(b.status in ('Confirmed','Checked-In') or (b.status='Pending' and b.created_at>datetime('now','-15 minutes')))"

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB, timeout=10); g.db.row_factory = sqlite3.Row; g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def _close(e):
    d = g.pop("db", None)
    if d: d.close()
def q(sql, a=(), one=False):
    r = db().execute(sql, a).fetchall(); return (r[0] if r else None) if one else r

def run(sql, a=()):
    c = db().execute(sql, a); db().commit(); return c.lastrowid

def init_db():
    c = sqlite3.connect(DB); c.executescript(open(os.path.join(app.root_path, "schema.sql")).read())
    if not c.execute("select 1 from users").fetchone():
        for t in ["Single Room", "Double Room", "Deluxe Room", "Luxury Room", "Family Room"]: c.execute("insert into room_types(name) values(?)", (t,))
        c.execute("insert into hotels(name,city,address,description) values('Grand Palace','Delhi','Connaught Place','Heritage stay in central Delhi')")
        c.execute("insert into hotels(name,city,address,description) values('Sea Breeze Resort','Goa','Calangute Beach','Beachfront resort')")
        c.executemany("insert into hotel_facilities(hotel_id,facility) values(?,?)", [(1, "WiFi"), (1, "Pool"), (2, "Beach access"), (2, "Spa")])
        c.executemany("insert into rooms(hotel_id,type_id,room_no,price,capacity,facilities) values(?,?,?,?,?,?)",
            [(1, 1, "101", 2500, 1, "AC, WiFi, TV"), (1, 2, "102", 3500, 2, "AC, WiFi, Minibar"), (1, 4, "201", 9000, 3, "AC, Jacuzzi, Butler"), (2, 3, "301", 6000, 2, "AC, Sea view"), (2, 5, "302", 8000, 5, "AC, Kitchenette, 2 beds")])
        for n, e, ph, pw, r, h in [("Admin", "admin@hotel.com", "9000000001", "Admin@123", "admin", None), ("Delhi Manager", "manager@hotel.com", "9000000002", "Manager@123", "manager", 1), ("Demo Guest", "guest@hotel.com", "9000000003", "Guest@123", "customer", None)]:
            c.execute("insert into users(name,email,phone,password_hash,role,hotel_id) values(?,?,?,?,?,?)", (n, e, ph, gph(pw), r, h))
    c.commit(); c.close()

def me(): return q("select * from users where id=?", (session["uid"],), one=True) if "uid" in session else None

def need(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            u = me()
            if not u: return redirect(url_for("login", next=request.path))
            if roles and u["role"] not in roles: abort(403)
            g.user = u; return f(*a, **k)
        return w
    return deco

@app.context_processor
def _ctx(): return dict(user=me())

def clean(s): return (s or "").strip()

def fld(n, l, t="text", o=None, v=None): return (n, l, t, request.form.get(n, "") if v is None else v, o)

def num(v, d, cast):
    try: return cast(v) if v not in (None, "") else d
    except ValueError: return d

def scope(): return (" and r.hotel_id=?", [g.user["hotel_id"]]) if g.user["role"] == "manager" else ("", [])

def table(title, headers, rows, **kw): return render_template("admin_list.html", title=title, headers=headers, rows=rows, **kw)
