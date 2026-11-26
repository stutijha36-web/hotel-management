from core import (
    app, clean, cph, datetime, flash,
    fld, g, gph, need, q,
    re, redirect, render_template, request, run,
    secrets, session, timedelta, url_for)

def check(f, pw=True):
    e = []
    if len(clean(f.get("name"))) < 2: e.append("Name must be at least 2 characters.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", clean(f.get("email"))): e.append("Enter a valid email.")
    if not re.fullmatch(r"\+?\d{10,13}", clean(f.get("phone"))): e.append("Phone must be 10-13 digits.")
    if pw and not re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d).{8,}", f.get("password", "")): e.append("Password needs 8+ characters with a letter and a number.")
    return e

def home_for(u): return "/admin" if u["role"] in ("admin", "manager") else "/"

@app.route("/register", methods=["GET", "POST"])
def register():
    f = request.form
    if request.method == "POST":
        err = check(f)
        if not err and q("select 1 from users where email=?", (clean(f["email"]).lower(),), one=True): err = ["Email already registered."]
        for e in err: flash(e)
        if not err:
            session["uid"] = run("insert into users(name,email,phone,password_hash) values(?,?,?,?)", (clean(f["name"]), clean(f["email"]).lower(), clean(f["phone"]), gph(f["password"])))
            return redirect("/")
    return render_template("form.html", title="Register", submit="Register", fields=[fld("name", "Full name"), fld("email", "Email", "email"), fld("phone", "Phone"), fld("password", "Password", "password")])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q("select * from users where email=?", (clean(request.form.get("email")).lower(),), one=True)
        if u and cph(u["password_hash"], request.form.get("password", "")):
            session.clear(); session["uid"] = u["id"]; nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else home_for(u))
        flash("Invalid email or password.")
    return render_template("form.html", title="Login", submit="Login", fields=[fld("email", "Email", "email"), fld("password", "Password", "password")], extra='<a href="/forgot">Forgot password?</a>')

@app.route("/logout")
def logout(): session.clear(); return redirect("/")

@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        u = q("select id from users where email=?", (clean(request.form.get("email")).lower(),), one=True)
        if u:
            t = secrets.token_urlsafe(24)
            run("update users set reset_token=?, reset_expires=? where id=?", (t, (datetime.utcnow() + timedelta(hours=1)).isoformat(), u["id"]))
            link = url_for("reset", token=t, _external=True)
            print("PASSWORD RESET LINK:", link)
            if app.debug: flash("Dev mode - reset link: " + link)
        flash("If that email exists, a reset link has been sent.")
    return render_template("form.html", title="Forgot password", submit="Send reset link", fields=[fld("email", "Email", "email")])

@app.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    u = q("select * from users where reset_token=? and reset_expires>?", (token, datetime.utcnow().isoformat()), one=True)
    if not u: flash("Reset link is invalid or expired."); return redirect("/login")
    if request.method == "POST":
        if re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d).{8,}", request.form.get("password", "")):
            run("update users set password_hash=?, reset_token=null where id=?", (gph(request.form["password"]), u["id"])); flash("Password updated. Please login."); return redirect("/login")
        flash("Password needs 8+ characters with a letter and a number.")
    return render_template("form.html", title="Set new password", submit="Update", fields=[fld("password", "New password", "password")])

@app.route("/profile", methods=["GET", "POST"])
@need()
def profile():
    u, f = g.user, request.form; c = q("select * from customers where user_id=?", (u["id"],), one=True)
    if request.method == "POST":
        err = check({**f, "email": u["email"]}, pw=False)
        if f.get("password"):
            if not cph(u["password_hash"], f.get("current", "")): err.append("Current password is wrong.")
            if not re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d).{8,}", f["password"]): err.append("New password needs 8+ characters with a letter and a number.")
        for e in err: flash(e)
        if not err:
            run("update users set name=?, phone=? where id=?", (clean(f["name"]), clean(f["phone"]), u["id"]))
            if f.get("password"): run("update users set password_hash=? where id=?", (gph(f["password"]), u["id"]))
            save_customer(u["id"], clean(f["name"]), clean(f["phone"]), clean(f.get("address"))); flash("Profile updated."); return redirect("/profile")
    return render_template("form.html", title="My profile", submit="Save", fields=[fld("name", "Name", v=u["name"]), fld("phone", "Phone", v=u["phone"]), fld("address", "Address", v=c["address"] if c else ""), fld("current", "Current password (only to change it)", "password"), fld("password", "New password", "password")])

def save_customer(uid, name, phone, addr):
    if q("select 1 from customers where user_id=?", (uid,), one=True): run("update customers set full_name=?, phone=?, address=? where user_id=?", (name, phone, addr, uid))
    else: run("insert into customers(user_id,full_name,phone,address) values(?,?,?,?)", (uid, name, phone, addr))
    return q("select id from customers where user_id=?", (uid,), one=True)["id"]
