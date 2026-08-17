from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)

app.secret_key = "eventbook_secret"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Shiv123@",
    database="event_booking_system"
)

@app.route("/")
def home():
    return render_template("index.html")
 
@app.route("/events")
def events():
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM events ORDER BY event_date ASC")

    events = cursor.fetchall()
    cursor.close()

    return render_template("events.html", events=events)
@app.route("/booking", methods=["GET", "POST"])
def bookings():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        event_id = request.form["event_id"]
        seats = request.form["seats"]
        user_id = session["user_id"]

        cursor = db.cursor()

        # Save booking
        cursor.execute(
            """
            INSERT INTO booking
            (user_id, event_id, number_of_seats, booking_date, status)
            VALUES (%s, %s, %s, NOW(), %s)
            """,
            (user_id, event_id, seats, "Confirmed")
        )

        booking_id = cursor.lastrowid

        # Reduce available seats
        cursor.execute(
            """
            UPDATE events
            SET available_seats = available_seats - %s
            WHERE event_id = %s
            """,
            (seats, event_id)
        )

        # Create notification
        cursor.execute(
            """
            INSERT INTO notifications
            (user_id, booking_id, title, message, notification_type, is_read)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                booking_id,
                "Booking Confirmed",
                "Your event booking has been confirmed successfully.",
                "booking",
                0
            )
        )

        db.commit()
        cursor.close()

        return redirect(url_for("events"))

    # GET: load events for booking dropdown
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT event_id, event_name
        FROM events
        WHERE event_date >= CURDATE()
        ORDER BY event_date ASC
        """
    )

    events = cursor.fetchall()
    cursor.close()

    return render_template("booking.html", events=events)

    

   
@app.route("/my-bookings")
def my_bookings():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
    SELECT booking_id, event_id, number_of_seats, booking_date, status
    FROM booking
    WHERE user_id = %s
    ORDER BY booking_date DESC
    """,
        (user_id,)
    )

    bookings = cursor.fetchall()
    print("USER ID:", user_id)
    print("BOOKINGS:", bookings)
    print("LOGIN USER ID=", user_id)
    print("BOOKINGS FOUND=", bookings)
    cursor.close()

    return render_template("my_bookings.html", bookings=bookings)

@app.route("/notifications")
def notifications():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT notification_id, booking_id, title, message,
        notification_type, is_read, created_at
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,)
    )

    notifications = cursor.fetchall()
    cursor.close()

    return render_template("notifications.html",notifications=notifications)

@app.route("/dashboard")
def dashboard():

    user_id = session.get("user_id")

    if not user_id:
        return redirect(url_for("login"))

    cursor = db.cursor(dictionary=True)

    # Total bookings
    cursor.execute(
        "SELECT COUNT(*) AS total FROM booking WHERE user_id = %s",
        (user_id,)
    )
    total_bookings = cursor.fetchone()["total"]

    # Upcoming events
    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM booking b
        JOIN events e ON b.event_id = e.event_id
        WHERE b.user_id = %s
        AND e.event_date >= CURDATE()
        """,
        (user_id,)
    )
    upcoming_events = cursor.fetchone()["total"]

    # Available events
    cursor.execute(
        "SELECT COUNT(*) AS total FROM events WHERE event_date >= CURDATE()"
    )
    available_events = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT b.booking_id,
            e.event_name,
            b.number_of_seats,
            b.booking_date,
            b.status
        FROM booking b
        JOIN events e ON b.event_id = e.event_id
        WHERE b.user_id = %s
        ORDER BY b.booking_date DESC
    """, (user_id,))

    bookings = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(number_of_seats), 0) AS total_seats
        FROM booking
        WHERE user_id = %s
""", (user_id,))

    my_activity = cursor.fetchone()["total_seats"]

    cursor.execute("""
    SELECT event_id,
           event_name,
           event_date,
           event_time,
           venue,
           available_seats
    FROM events
    WHERE event_date >= CURDATE()
    ORDER BY event_date ASC
""")

    upcoming_event_list = cursor.fetchall()

    cursor.close()

    return render_template(
        "dashboard.html",
        total_bookings=total_bookings,
        upcoming_events=upcoming_events,
        available_events=available_events,bookings=bookings,
        my_activity=my_activity,
        upcoming_event_list=upcoming_event_list
    )

@app.route("/add-event", methods=["GET", "POST"])
def add_event():
    if request.method == "POST":
        event_name = request.form["event_name"]
        description = request.form["description"]
        event_date = request.form["event_date"]
        event_time = request.form["event_time"]
        venue = request.form["venue"]
        available_seats = request.form["available_seats"]
        banner_image = request.form["banner_image"]

        cursor = db.cursor()

        cursor.execute("""
            INSERT INTO events
            (event_name, description, banner_image, event_date,
             event_time, venue, available_seats)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            event_name,
            description,
            banner_image,
            event_date,
            event_time,
            venue,
            available_seats
        ))

        db.commit()
        cursor.close()

        return redirect(url_for("events"))

    return render_template("add_event.html")

@app.route("/edit-event/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):

    cursor = db.cursor(dictionary=True)

    if request.method == "POST":

        event_name = request.form["event_name"]
        description = request.form["description"]
        event_date = request.form["event_date"]
        event_time = request.form["event_time"]
        venue = request.form["venue"]
        available_seats = request.form["available_seats"]
        banner_image = request.form["banner_image"]

        cursor.execute("""
            UPDATE events
            SET event_name = %s,
                description = %s,
                banner_image = %s,
                event_date = %s,
                event_time = %s,
                venue = %s,
                available_seats = %s
            WHERE event_id = %s
        """, (
            event_name,
            description,
            banner_image,
            event_date,
            event_time,
            venue,
            available_seats,
            event_id
        ))

        db.commit()
        cursor.close()

        return redirect(url_for("events"))

    cursor.execute(
        "SELECT * FROM events WHERE event_id = %s",
        (event_id,)
    )

    event = cursor.fetchone()
    cursor.close()

    if not event:
        return "Event not found", 404

    return render_template("edit_event.html", event=event)



@app.route("/delete-event/<int:event_id>")
def delete_event(event_id):
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM events WHERE event_id = %s",
        (event_id,)
    )

    db.commit()
    cursor.close()

    return redirect(url_for("events"))

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor()

        query = """
        INSERT INTO users (name, email, password)
        VALUES (%s, %s, %s)
        """

        cursor.execute(query, (name, email, password))
        db.commit()

        cursor.close()

        return "Registration Successful!"

    return render_template("register.html") 

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cursor.fetchone()
        cursor.close()

        if user:
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))

            return render_template("login.html", error="Invalid email or password")

        return "Invalid email or password"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login")) 
   



if __name__ == "__main__":
    app.run(debug=True)