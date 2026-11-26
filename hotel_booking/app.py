from core import *
import auth, hotels, search, booking, payments     


if __name__ == "__main__":
    init_db()
    app.run(debug=True)