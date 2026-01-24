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
