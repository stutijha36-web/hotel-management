

from core import (
    HOLD, SERVICE, TAX, abort, app,
    clean, date, flash, num, q,
    render_template, request)


def parse_dates(v):
    try: ci, co = date.fromisoformat(v["check_in"]), date.fromisoformat(v["check_out"])
    except (KeyError, ValueError, TypeError): return None
    return (ci, co) if date.today() <= ci < co else None


def is_free(rid, ci, co, skip=0):
    return not q(f"select 1 from bookings b where b.room_id=? and b.id!=? and {HOLD} and b.check_in<? and b.check_out>?", (rid, skip, co.isoformat(), ci.isoformat()), one=True)


ROOMQ = "select r.*, h.name hotel, h.city, t.name type from rooms r join hotels h on h.id=r.hotel_id join room_types t on t.id=r.type_id "


@app.route("/")
def search():
    f, rooms, d = request.args, None, None
    if f.get("check_in"):
        d = parse_dates(f)
        if not d: flash("Check-in must be today or later and check-out after check-in.")
        else:
            sql, a = ROOMQ + "where r.active=1 and lower(h.city) like ? and r.capacity>=? and r.price<=?", [f"%{clean(f.get('city')).lower()}%", num(f.get("guests"), 1, int), num(f.get("max_price"), 1e9, float)]
            if f.get("type"): sql += " and t.id=?"; a.append(num(f["type"], 0, int))
            rooms = [r for r in q(sql + " order by r.price", a) if is_free(r["id"], *d)]
    return render_template("search.html", rooms=rooms, types=q("select * from room_types"), f=f, today=date.today().isoformat())


def quote(room, ci, co):
    n = (co - ci).days; base = room["price"] * n; tax, svc = round(base * TAX, 2), round(base * SERVICE, 2)
    return dict(nights=n, base=base, tax=tax, svc=svc, total=round(base + tax + svc, 2))


def get_room(rid):
    r = q(ROOMQ + "where r.id=? and r.active=1", (rid,), one=True) or abort(404); return r


@app.route("/room/<int:rid>")
def room(rid):
    r, d = get_room(rid), parse_dates(request.args)
    return render_template("room.html", r=r, d=d, qt=quote(r, *d) if d else None, f=request.args, today=date.today().isoformat(),
        fac=q("select facility from hotel_facilities where hotel_id=?", (r["hotel_id"],)), reviews=q("select v.*, u.name from reviews v join users u on u.id=v.user_id where v.room_id=? order by v.id desc", (rid,)))
