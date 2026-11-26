import csv
import io
from datetime import datetime
from flask import request, Response, url_for, flash, redirect
from core import app, q, need, scope, table

REPORTS = {
    "daily": ("Daily bookings", ["Date", "Bookings", "Booked value"],
              "select date(b.created_at), count(*), round(sum(b.total),2) "
              "from bookings b join rooms r on r.id=b.room_id "
              "where b.status!='Cancelled'{s} group by 1 order by 1 desc"),

    "monthly": ("Monthly revenue", ["Month", "Payments", "Revenue"],
                "select strftime('%Y-%m',p.paid_at), count(*), round(sum(p.amount),2) "
                "from payments p join bookings b on b.id=p.booking_id "
                "join rooms r on r.id=b.room_id "
                "where p.status='Paid'{s} group by 1 order by 1 desc"),

    "occupancy": ("Room occupancy", ["Hotel", "Room", "Nights booked", "Occupied now"],
                  "select h.name, r.room_no, "
                  "coalesce(sum(case when b.status!='Cancelled' then b.nights end),0), "
                  "coalesce(max(b.status='Checked-In'),0) "
                  "from rooms r join hotels h on h.id=r.hotel_id "
                  "left join bookings b on b.room_id=r.id "
                  "where 1{s} group by r.id order by h.name, r.room_no"),

    "customers": ("Customer bookings", ["Customer", "Email", "Bookings", "Total spent"],
                  "select u.name, u.email, count(*), round(sum(b.total),2) "
                  "from bookings b join users u on u.id=b.user_id "
                  "join rooms r on r.id=b.room_id "
                  "where b.status!='Cancelled'{s} group by u.id order by 4 desc"),
}


def make_pdf(title, headers, data):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
    styles = getSampleStyleSheet()
    rows = [headers] + [[str(c) for c in r] for r in data]
    t = Table(rows, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#083b3d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f3f7f6")]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    stamp = datetime.now().strftime("%d %b %Y, %H:%M")
    doc.build([Paragraph("StayEasy Hotels", styles["Title"]),
               Paragraph(f"{title} - generated {stamp}", styles["Normal"]),
               Spacer(1, 12), t])
    return buf.getvalue()


@app.route("/admin/reports")
@need("admin", "manager")
def reports():
    s, a = scope()
    kind = request.args.get("type", "daily")
    if kind not in REPORTS:
        kind = "daily"
    title, headers, sql = REPORTS[kind]
    data = [list(r) for r in q(sql.format(s=s), a)]
    fmt = request.args.get("fmt")

    if fmt == "csv":
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(headers)
        w.writerows(data)
        return Response(out.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition":
                                 f"attachment; filename={kind}_report.csv"})

    if fmt == "pdf":
        try:
            pdf = make_pdf(title, headers, data)
        except ImportError:
            flash("PDF needs reportlab. Run: pip install reportlab")
            return redirect(url_for("reports", type=kind))
        return Response(pdf, mimetype="application/pdf",
                        headers={"Content-Disposition":
                                 f"attachment; filename={kind}_report.pdf"})

    rows = [dict(cells=r, actions=[]) for r in data]
    return table(title, headers, rows,
                 tabs=[(k, v[0]) for k, v in REPORTS.items()],
                 export=url_for("reports", type=kind, fmt="csv"),
                 export_pdf=url_for("reports", type=kind, fmt="pdf"))