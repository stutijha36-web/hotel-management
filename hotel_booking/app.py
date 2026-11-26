
from core import app, init_db

import auth
import hotels
import search
import booking
import payments

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
