from core import (
    UPLOAD, abort, app, clean, flash,
    fld, g, need, num, os,
    q, redirect, request, run, scope,
    secrets, sqlite3, table, url_for)
from search import ROOMQ

@app.route("/admin/hotels", methods=["GET", "POST"])
@need("admin")
def hotels():
    eid = request.args.get("edit", type=int); h = q("select * from hotels where id=?", (eid,), one=True) if eid else None; f = request.form
    if request.method == "POST":
        name, city = clean(f.get("name")), clean(f.get("city"))
        if len(name) < 2 or len(city) < 2: flash("Hotel name and city are required.")
        else:
            a = (name, city, clean(f.get("address")), clean(f.get("description")))
            if eid: run("update hotels set name=?,city=?,address=?,description=? where id=?", a + (eid,))
            else: eid = run("insert into hotels(name,city,address,description) values(?,?,?,?)", a)
            run("delete from hotel_facilities where hotel_id=?", (eid,))
            for x in {s.strip() for s in f.get("facilities", "").split(",") if s.strip()}: run("insert into hotel_facilities(hotel_id,facility) values(?,?)", (eid, x))
            return redirect(url_for("hotels"))
    fac = ", ".join(r[0] for r in q("select facility from hotel_facilities where hotel_id=?", (eid,))) if eid else ""
    g_ = lambda k: (h[k] or "") if h else ""
    fields = [fld("name", "Hotel name", v=g_("name")), fld("city", "City", v=g_("city")), fld("address", "Address", v=g_("address")), fld("description", "Description", "textarea", v=g_("description")), fld("facilities", "Facilities (comma separated)", v=fac)]
    rows = [dict(cells=[x["name"], x["city"], x["address"]], actions=[("Edit", url_for("hotels", edit=x["id"]), "get"), ("Delete", url_for("del_hotel", hid=x["id"]), "post")]) for x in q("select * from hotels")]
    return table("Hotels", ["Name", "City", "Address"], rows, fields=fields, submit="Update hotel" if h else "Add hotel")

@app.route("/admin/hotels/<int:hid>/delete", methods=["POST"])
@need("admin")
def del_hotel(hid):
    try: run("delete from hotels where id=?", (hid,)); flash("Hotel deleted.")
    except sqlite3.IntegrityError: flash("Hotel has bookings/staff and cannot be deleted.")
    return redirect(url_for("hotels"))

@app.route("/admin/rooms", methods=["GET", "POST"])
@need("admin", "manager")
def rooms_admin():
    s, a = scope(); eid = request.args.get("edit", type=int); f = request.form
    rm = q("select r.* from rooms r where r.id=?" + s, [eid] + a, one=True) if eid else None
    if request.method == "POST":
        hid = g.user["hotel_id"] if s else num(f.get("hotel_id"), 0, int); price, cap = num(f.get("price"), 0, float), num(f.get("capacity"), 0, int); err = []
        if not q("select 1 from hotels where id=?", (hid,), one=True): err.append("Choose a hotel.")
        if not clean(f.get("room_no")): err.append("Room number required.")
        if price <= 0 or cap < 1: err.append("Price and capacity must be positive.")
        img, fn = request.files.get("image"), (rm["image"] if rm else None)
        if img and img.filename:
            ext = img.filename.rsplit(".", 1)[-1].lower()
            if ext not in ("jpg", "jpeg", "png", "webp"): err.append("Image must be jpg, png or webp.")
            else: fn = secrets.token_hex(8) + "." + ext
        for e in err: flash(e)
        if not err:
            v = (hid, num(f.get("type_id"), 1, int), clean(f["room_no"]), price, cap, clean(f.get("facilities")), fn, 1 if f.get("active", "1") == "1" else 0)
            try:
                if eid and rm: run("update rooms set hotel_id=?,type_id=?,room_no=?,price=?,capacity=?,facilities=?,image=?,active=? where id=?", v + (eid,))
                else: run("insert into rooms(hotel_id,type_id,room_no,price,capacity,facilities,image,active) values(?,?,?,?,?,?,?,?)", v)
                if img and img.filename and fn: os.makedirs(UPLOAD, exist_ok=True); img.save(os.path.join(UPLOAD, fn))
                return redirect(url_for("rooms_admin"))
            except sqlite3.IntegrityError: flash("That room number already exists in this hotel.")
    g_ = lambda k, d="": rm[k] if rm else d
    fields = ([] if s else [fld("hotel_id", "Hotel", "select", [(x["id"], x["name"]) for x in q("select * from hotels")], g_("hotel_id"))]) + [
        fld("type_id", "Room type", "select", [(x["id"], x["name"]) for x in q("select * from room_types")], g_("type_id")), fld("room_no", "Room no.", v=g_("room_no")),
        fld("price", "Price per night", "number", v=g_("price")), fld("capacity", "Capacity", "number", v=g_("capacity")), fld("facilities", "Facilities", v=g_("facilities") or ""),
        fld("active", "Status", "select", [("1", "Active"), ("0", "Inactive")], str(g_("active", 1))), fld("image", "Image", "file")]
    rows = [dict(cells=[x["hotel"], x["room_no"], x["type"], x["price"], x["capacity"], "Active" if x["active"] else "Inactive"], actions=[("Edit", url_for("rooms_admin", edit=x["id"]), "get"), ("Delete", url_for("del_room", rid=x["id"]), "post")])
            for x in q(ROOMQ + "where 1" + s, a)]
    return table("Rooms", ["Hotel", "Room", "Type", "Price", "Cap.", "Status"], rows, fields=fields, submit="Update room" if rm else "Add room")

@app.route("/admin/rooms/<int:rid>/delete", methods=["POST"])
@need("admin", "manager")
def del_room(rid):
    s, a = scope()
    if not q("select 1 from rooms r where r.id=?" + s, [rid] + a, one=True): abort(403)
    try: run("delete from rooms where id=?", (rid,)); flash("Room deleted.")
    except sqlite3.IntegrityError: run("update rooms set active=0 where id=?", (rid,)); flash("Room has bookings, so it was deactivated instead.")
    return redirect(url_for("rooms_admin"))
