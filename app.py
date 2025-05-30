# app.py
from flask import Flask, render_template, request, redirect, url_for
from connect import get_connection
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/events')
def events():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM events ORDER BY event_date")
    events_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('events.html', events=events_list)

@app.route('/events/<int:event_id>/customers')
def event_customer_list(event_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get event details
    cursor.execute("SELECT event_name, event_date FROM events WHERE event_id = %s", (event_id,))
    event = cursor.fetchone()

    # Get customers for this event
    cursor.execute("""
        SELECT c.customer_id, c.first_name, c.family_name, c.date_of_birth
        FROM customers c
        JOIN ticket_sales t ON c.customer_id = t.customer_id
        WHERE t.event_id = %s
        ORDER BY c.family_name ASC, c.date_of_birth DESC
    """, (event_id,))
    customers = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("eventcustomerlist.html", event=event, customers=customers)

@app.route('/tickets/buy', methods=['GET', 'POST'])
def buy_tickets():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        customer_id = request.form['customer_id']
        event_id = request.form['event_id']
        ticket_count = int(request.form['ticket_count'])

        # Get event details
        cursor.execute("SELECT event_date, age_restriction, capacity FROM events WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()

        # Get customer details
        cursor.execute("SELECT date_of_birth FROM customers WHERE customer_id = %s", (customer_id,))
        customer = cursor.fetchone()

        # Age validation
        today = datetime.today()
        dob = customer['date_of_birth']
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        if age < event['age_restriction']:
            message = "Customer does not meet the age requirement for this event."
            cursor.close()
            conn.close()
            return render_template("buy_tickets.html", message=message)

        # Check for future event
        if event['event_date'] <= datetime.now().date():
            message = "Cannot purchase tickets for past events."
            cursor.close()
            conn.close()
            return render_template("buy_tickets.html", message=message)

        # Check remaining tickets
        cursor.execute("SELECT SUM(ticket_count) AS sold FROM ticket_sales WHERE event_id = %s", (event_id,))
        sold = cursor.fetchone()['sold'] or 0
        available = event['capacity'] - sold
        if ticket_count > available:
            message = f"Only {available} tickets available for this event."
            cursor.close()
            conn.close()
            return render_template("buy_tickets.html", message=message)

        # Insert ticket sale
        cursor.execute(
            "INSERT INTO ticket_sales (customer_id, event_id, ticket_count) VALUES (%s, %s, %s)",
            (customer_id, event_id, ticket_count)
        )
        conn.commit()
        message = "Tickets purchased successfully."

        cursor.close()
        conn.close()
        return render_template("buy_tickets.html", message=message)

    # GET request
    cursor.execute("SELECT customer_id, first_name, family_name FROM customers ORDER BY family_name")
    customers = cursor.fetchall()

    cursor.execute("SELECT event_id, event_name, event_date FROM events WHERE event_date > %s", (datetime.now().date(),))
    events = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template("buy_tickets.html", customers=customers, events=events)

@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        family_name = request.form['family_name'].strip()
        date_of_birth = request.form['date_of_birth']
        email = request.form['email'].strip()
        phone = request.form['phone'].strip()

        # Basic validation
        if not (first_name and family_name and date_of_birth and email and phone):
            message = "All fields are required."
            return render_template("add_customer.html", message=message)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customers (first_name, family_name, date_of_birth, email, phone)
            VALUES (%s, %s, %s, %s, %s)
        """, (first_name, family_name, date_of_birth, email, phone))
        conn.commit()
        cursor.close()
        conn.close()

        message = "Customer added successfully."
        return render_template("add_customer.html", message=message)

    return render_template("add_customer.html")

@app.route('/customers/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        first_name = request.form['first_name'].strip()
        family_name = request.form['family_name'].strip()
        date_of_birth = request.form['date_of_birth']
        email = request.form['email'].strip()
        phone = request.form['phone'].strip()

        if not (first_name and family_name and date_of_birth and email and phone):
            message = "All fields are required."
            # Fetch existing data again
            cursor.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
            customer = cursor.fetchone()
            cursor.close()
            conn.close()
            return render_template("edit_customer.html", customer=customer, message=message)

        cursor.execute("""
            UPDATE customers
            SET first_name = %s,
                family_name = %s,
                date_of_birth = %s,
                email = %s,
                phone = %s
            WHERE customer_id = %s
        """, (first_name, family_name, date_of_birth, email, phone, customer_id))
        conn.commit()
        message = "Customer updated successfully."

    # GET request or POST with validation error
    cursor.execute("SELECT * FROM customers WHERE customer_id = %s", (customer_id,))
    customer = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template("edit_customer.html", customer=customer, message=message if 'message' in locals() else None)

@app.route('/customers/search', methods=['GET', 'POST'])
def customer_search():
    results = []
    if request.method == 'POST':
        keyword = request.form['keyword'].strip()
        if keyword:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT customer_id, first_name, family_name, email, phone
                FROM customers
                WHERE first_name LIKE %s OR family_name LIKE %s
                ORDER BY family_name, first_name
            """
            cursor.execute(query, (f'%{keyword}%', f'%{keyword}%'))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
    return render_template("customer_search.html", results=results)

@app.route('/customers/<int:customer_id>/summary')
def customer_summary(customer_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get customer info
    cursor.execute("SELECT first_name, family_name FROM customers WHERE customer_id = %s", (customer_id,))
    customer = cursor.fetchone()

    # Get all ticket purchases
    cursor.execute("""
        SELECT e.event_name, e.event_date, t.ticket_count
        FROM ticket_sales t
        JOIN events e ON t.event_id = e.event_id
        WHERE t.customer_id = %s
        ORDER BY e.event_date ASC
    """, (customer_id,))
    purchases = cursor.fetchall()

    # Calculate total tickets
    total_tickets = sum(p['ticket_count'] for p in purchases)

    cursor.close()
    conn.close()

    return render_template(
        "customer_summary.html",
        customer=customer,
        purchases=purchases,
        total_tickets=total_tickets
    )

@app.route('/events/available')
def available_events():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Get events with remaining tickets and future date
    cursor.execute("""
        SELECT 
            e.event_id,
            e.event_name,
            e.event_date,
            e.capacity,
            COALESCE(SUM(t.ticket_count), 0) AS sold
        FROM events e
        LEFT JOIN ticket_sales t ON e.event_id = t.event_id
        WHERE e.event_date > %s
        GROUP BY e.event_id
        HAVING (e.capacity - sold) > 0
        ORDER BY e.event_date ASC
    """, (datetime.now().date(),))

    events = cursor.fetchall()
    for event in events:
        event['remaining'] = event['capacity'] - event['sold']

    cursor.close()
    conn.close()

    return render_template("available_events.html", events=events)

if __name__ == '__main__':
    app.run(debug=True)
