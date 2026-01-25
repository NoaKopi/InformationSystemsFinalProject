# Information Systems Final Project – FLYTAU

## Project Overview
FLYTAU is a flight booking and management system developed as part of the Information Systems final project.
The system supports flight search, booking, order management, registration to the system and administrative control over flights and workers.

The project focuses on correct database design, SQL querying, and integration with a Python-based backend.

---

## Technologies
- Python (Flask)
- SQLite
- SQL
- HTML / CSS

---

## Project Structure
- `main.py` – Application entry point and route definitions
- `utils/` – Business logic and helper functions
- `templates/` – HTML templates (client and admin views)
- `static/` – CSS and images needed 
- `FLYTAU15.sql` – Database schema and SQL queries

---

## Database
The project uses **SQLite** as the database engine.
- The database schema and queries are provided in `FLYTAU15.sql`

---

## User Features

The system supports two types of customers: **Unidentified Guests** and **Registered Users**.

### Unidentified Guests
Unidentified Guests can use the system without creating an account.

Unidentified Guests can:
- Search for available flights by origin, destination, departuer date
- View flight details and seat availability, devided by class
- Book flight tickets and select seats
- Complete an order using an email address 
- View active orders using order ID and email
- Cancel active orders according to the system cancellation policy

### Registered Users
Registered users create an account and log in using their email and password.

Registered users can do all the actions Unidentified Guests can, and in addition:
- View full order history, including completed and cancelled orders
- Automatically use saved personal details when placing new orders

During registration, the system stores:
- Passport ID
- Full name (in English)
- Date of birth
- Email and password
- Registration date

---

## Admin Features
- View and filter flights by origin, destination, date, and status
- Automatic update of flight status to `done` when departure time has passed
- Flight cancellation with a 72-hour rule
- Completed flights (`done`) cannot be cancelled
- System cancellation automatically updates related orders and seat availability

---

## Notes
This repository includes only the project source code.
Local database files are not part of the submission.
