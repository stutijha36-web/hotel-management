CREATE TABLE IF NOT EXISTS hotels(id INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL, address TEXT, description TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN('customer','admin','manager')), hotel_id INTEGER REFERENCES hotels(id), reset_token TEXT, reset_expires TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS hotel_facilities(id INTEGER PRIMARY KEY, hotel_id INTEGER NOT NULL REFERENCES hotels(id) ON DELETE CASCADE, facility TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS room_types(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY, hotel_id INTEGER NOT NULL REFERENCES hotels(id) ON DELETE CASCADE, type_id INTEGER NOT NULL REFERENCES room_types(id),
  room_no TEXT NOT NULL, price REAL NOT NULL CHECK(price>0), capacity INTEGER NOT NULL CHECK(capacity>0), facilities TEXT, image TEXT, active INTEGER DEFAULT 1, UNIQUE(hotel_id,room_no));
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE NOT NULL REFERENCES users(id), full_name TEXT, phone TEXT, address TEXT);
CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id), customer_id INTEGER REFERENCES customers(id),
  room_id INTEGER NOT NULL REFERENCES rooms(id), check_in TEXT NOT NULL, check_out TEXT NOT NULL, guests INTEGER NOT NULL, nights INTEGER NOT NULL,
  base_amount REAL, tax REAL, service_charge REAL, total REAL, status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN('Pending','Confirmed','Checked-In','Checked-Out','Cancelled')),
  created_at TEXT DEFAULT CURRENT_TIMESTAMP, CHECK(check_out>check_in));
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY, booking_id INTEGER NOT NULL REFERENCES bookings(id), amount REAL NOT NULL, method TEXT, txn_id TEXT,
  status TEXT NOT NULL DEFAULT 'Paid', receipt_no TEXT UNIQUE, paid_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS reviews(id INTEGER PRIMARY KEY, booking_id INTEGER UNIQUE NOT NULL REFERENCES bookings(id), user_id INTEGER NOT NULL REFERENCES users(id),
  room_id INTEGER NOT NULL REFERENCES rooms(id), rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5), comment TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS booking_history(id INTEGER PRIMARY KEY, booking_id INTEGER NOT NULL REFERENCES bookings(id), status TEXT, note TEXT, changed_by INTEGER, changed_at TEXT DEFAULT CURRENT_TIMESTAMP);
