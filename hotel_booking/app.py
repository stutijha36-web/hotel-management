
from core import app, init_db

import auth
import hotels
import search
import booking
import payments
import bookings
import dashboard
import reports
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
