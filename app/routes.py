from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import secrets
from .db import getDBconnection
from .emailController import send_password_reset_email, send_welcome_email, send_ticket_update_email, send_new_ticket_email
from .auditLog import newAuditLog
from .openAI import openAIapicall

main = Blueprint('main', __name__)
DEFAULT_RESOLVER_USERNAME = "Auto assign resolver"

support_types = {
    "network support",
    "system support",
    "desktop support",
    "hardware support",
    "installation support",
    "general support"
}

def detect_support_type(title, description, id):
    openAI_response = openAIapicall(title, description)
    if openAI_response["resolver_team"] in support_types:
        newAuditLog(session.get("user"), f"OpenAI detected support type {openAI_response['resolver_team']} for ticket with title: {title}")
        connection = getDBconnection()
        try:
            connection.execute(
                """
                UPDATE requests
                SET detected_support_type = ?, priority = ?, reason = ?, category = ?
                WHERE request_id = ?
                """,
                (openAI_response["resolver_team"], openAI_response["priority"], openAI_response["reason"], openAI_response["category"], id)
            )
            resolver = connection.execute(
                "SELECT resolver_username FROM requests WHERE request_id = ?",
                (id,)).fetchone()  
            
            connection.commit()
        finally:
            connection.close()

        if resolver and resolver["resolver_username"] == DEFAULT_RESOLVER_USERNAME:
            auto_email_resolvers(connection, DEFAULT_RESOLVER_USERNAME, openAI_response["resolver_team"])

        return openAI_response
    newAuditLog(session.get("user"), f"OpenAI failed to detect support type for ticket with title: {title}, it returned {openAI_response}")
    return None

def auto_email_resolvers(connection, id, detected_support_type):
    user_columns = {
        column["name"]
        for column in connection.execute("PRAGMA table_info(users)").fetchall()
    }

    candidates = connection.execute(
        """
        SELECT username, email_address
        FROM users
        WHERE level = 1 AND support_type = ?
        ORDER BY username
        """,
        (detected_support_type,),
    ).fetchall()
    if not candidates:
        return None

    for candidate in candidates:
        send_new_ticket_email(candidate["email_address"], candidate["username"], id, detected_support_type)

@main.route("/")
def index():
    return render_template("index.html")

#Guard
def adminGuard():
    if session.get("user") is None:
        return redirect(url_for("main.login"))
    if session.get("level") != 0:
        return redirect(url_for("main.index"))
    return None

def loggedInGuard():
    if session.get("user") is None:
        return redirect(url_for("main.login"))
    return None

def ownsTheTicketOrIsAdminGuard(request_id):
    if loggedInGuard() is not None:
        return loggedInGuard()
    if adminGuard() is None:
        return None
    connection = getDBconnection()
    try:
        ticketUsername = connection.execute(
            "SELECT username, resolver_username FROM requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
    finally:
        connection.close()
    if ticketUsername is None:
        return redirect(url_for("main.index", error="Ticket not found"))
    if session.get("user") != ticketUsername["username"] and session.get("user") != ticketUsername["resolver_username"]:
        return redirect(url_for("main.index", error="Access denied"))
    return None
    
#routes for user control
@main.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")


        connection = getDBconnection()
        try:
            user = connection.execute(
                "SELECT password_hash, level FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        finally:
            connection.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user"] = username
            session["level"] = user["level"]
            newAuditLog(username, "Login")
            return redirect(url_for("main.index"))
        error = "Invalid credentials. Please contact an admin with code."
    return render_template("login.html", error=error)

@main.route("/logout", methods=["POST"])
def logout():
    guard = loggedInGuard()
    if guard is not None:
        return guard
    session.pop("user", None)
    session.pop("level", None)
    return redirect(url_for("main.index"))

@main.route("/updatepassword", methods=["GET", "POST"])
def updatepassword():
    guard = loggedInGuard()
    if guard is not None:
        return guard
    if request.method == "GET":
        return render_template("updatePassword.html")
    username = session.get("user")
    currentPass = request.form.get("currentPassword", "")
    newPass = request.form.get("newPassword", "")
    confirmPass = request.form.get("confirmPassword", "")
    error = None

    if not currentPass or not newPass or not confirmPass:
        return render_template("updatePassword.html", error="Required input is missing")
    if newPass != confirmPass:
        return render_template("updatePassword.html", error="New passwords do not match")
    
    connection = getDBconnection()
    try:
        user = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], currentPass):
            return render_template("updatePassword.html", error="Current password is wrong")
        
        newPassHash = generate_password_hash(newPass)
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (newPassHash, username)
        )
        connection.commit()
    finally:
        connection.close()
        newAuditLog(username, "Password updated")
    return redirect(url_for("main.index", message="Your password has been updated"))

@main.route("/forgotpassword", methods=["GET", "POST"])
def forgotPassword():
    if request.method == "GET":
        return render_template("forgotPassword.html")
    email = request.form.get("email", "").strip()
    if not email:
        return render_template("forgotPassword.html", error="email is required")

    connection = getDBconnection()
    user = None
    try:
        user = connection.execute(
            "SELECT username, email_address FROM users WHERE email_address = ?",
            (email,),
        ).fetchone()

        if user:
            tempPass = secrets.token_urlsafe(16)
            tempPassHash = generate_password_hash(tempPass)
            connection.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (tempPassHash, user["username"]),
            )
            connection.commit()
            if not send_password_reset_email(user["email_address"], user["username"], tempPass):
                return render_template("forgotPassword.html", error="Failed to send email")
    finally:
        connection.close()
        if user:
            newAuditLog(user["username"], "Temporary password issued via forgot password")
    return render_template("login.html", message="temporary password has been sent to your email")

#Routes for Admins
@main.route("/admin")
def admin():
    guard = adminGuard()
    if guard is not None:
        return guard

    connection = getDBconnection()
    try:
        users = connection.execute(
            "SELECT username, password_hash, level, support_type, email_address, create_date FROM users ORDER BY create_date DESC"
        ).fetchall()
    finally:
        connection.close()
    return render_template("admin.html", users=users)

@main.route("/admin/auditlog")
def auditlog():
    guard = adminGuard()
    if guard is not None:
        return guard
    
    connection = getDBconnection()
    try:
        logs = connection.execute(
            "SELECT id, username, action, date_time FROM audit_logs ORDER BY id DESC"
        ).fetchall()
    finally:
        connection.close()
    return render_template("auditLog.html", logs=logs)

@main.route("/admin/removeuser/", methods=["POST"])
def removeuser():
    guard = adminGuard()
    if guard is not None:
        return guard
    # TODO: remove the user
    return redirect(url_for("main.admin"))

@main.route("/admin/adduser", methods=["GET", "POST"])
def adduser():
    guard = adminGuard()
    if guard is not None:
        return guard

    if request.method == "GET":
        return render_template("newUser.html", support_types=support_types)
    
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip() or None
    level_raw = request.form.get("level", "").strip()
    support_type = request.form.get("support_type", "").strip() or None
    password = request.form.get("password", "")
    error = None
    user_created = False

    if not username or not password:
        return render_template("newUser.html", error="Username and password are required.", support_types=support_types)
    else:
        try:
            level = int(level_raw) if level_raw else None
        except ValueError:
            level = None
            return render_template("newUser.html", error="Level must be a number.", support_types=support_types)

    if not email:
        return render_template("newUser.html", error="Email is required", support_types=support_types)

    if level == 1:
        if support_type not in support_types:
            return render_template("newUser.html", error="Level 1 users must have a support type", support_types=support_types)
    connection = getDBconnection()
    try:
        existing = connection.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if existing:
            error = "That username is already taken."
        else:
            password_hash = generate_password_hash(password)
            connection.execute(
                """
                INSERT INTO users (username, password_hash, level, email_address, support_type)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, password_hash, level, email, support_type),
            )
            connection.commit()
            user_created = True
            return redirect(url_for("main.adduser", message=f"User {username} created"))
    finally:
        connection.close()
        if user_created:
            newAuditLog(session.get("user"), f"Added user {username}")
            send_welcome_email(email, username)

    return render_template("newUser.html", error=error, support_types=support_types)

#Routes for ticket management
@main.route("/tickets")
def tickets():
    guard = loggedInGuard()
    if guard is not None:
        return guard

    error = None
    connection = getDBconnection()
    try:
        if session.get("level") == 0:
            tickets = connection.execute(
                """
                SELECT r.request_id, r.request_title, r.request_body, r.username, r.resolver_username, r.create_date
                FROM requests r
                ORDER BY r.create_date DESC
                """
            ).fetchall()
        else:
            tickets = connection.execute(
                """
                SELECT r.request_id, r.request_title, r.request_body, r.username, r.resolver_username, r.create_date
                FROM requests r
                WHERE r.username = ? OR r.resolver_username = ?
                ORDER BY r.create_date DESC
                """,
                (session.get("user"), session.get("user")),
            ).fetchall()
    finally:
        connection.close()

    return render_template("tickets.html", tickets=tickets) 

@main.route("/ticket/<int:requestID>")
def ticket(requestID):
    guard = ownsTheTicketOrIsAdminGuard(requestID)
    if guard is not None:
        return guard
    connection = getDBconnection()
    try:
        ticketData = connection.execute(
            "SELECT request_id, request_title, request_body, username, resolver_username, create_date, open_close_status, close_date, detected_support_type, priority, reason, category FROM requests WHERE request_id = ?",
            (requestID,),
        ).fetchone()

        messages = connection.execute(
            """
            SELECT message_id, username, message_body, create_date
            FROM messages
            WHERE request_id = ?
            ORDER BY create_date ASC
            """,
            (requestID,),
        ).fetchall()
    finally:
        connection.close()

    if ticketData is None:
        return render_template("tickets.html", error=f"ticket was not found {requestID}")

    return render_template("ticket.html", ticket=ticketData, messages=messages)

@main.route("/closeticket", methods=["POST"])
def closeticket():
    request_id_raw = request.form.get("request_id", "").strip()
    if not request_id_raw.isdigit():
        return redirect(url_for("main.tickets", error="Invalid ticket id"))
    request_id = int(request_id_raw)
    guard = ownsTheTicketOrIsAdminGuard(request_id)
    if guard is not None:
        return guard
    connection = getDBconnection()
    try:
        connection.execute(
            """
            UPDATE requests
            SET open_close_status = 0, close_date = CURRENT_TIMESTAMP
            WHERE request_id = ?
            """,
            (request_id,),
        )
        connection.commit()
    finally:
        connection.close()
    newAuditLog(session.get("user"), f"Closed ticket with id {request_id}")
    return redirect(url_for("main.ticket", requestID=request_id))

@main.route("/ticket/<int:requestID>/message", methods=["POST"])
def add_message(requestID):
    guard = ownsTheTicketOrIsAdminGuard(requestID)
    if guard is not None:
        return guard

    body = request.form.get("message", "").strip()
    if not body:
        return redirect(url_for("main.ticket", requestID=requestID))

    connection = getDBconnection()
    try:
        connection.execute(
            """
            INSERT INTO messages (request_id, username, message_body)
            VALUES (?, ?, ?)
            """,
            (requestID, session.get("user"), body),
        )
        connection.commit()
    finally:
        connection.close()

    return redirect(url_for("main.ticket", requestID=requestID))

@main.route("/addticket", methods=["GET", "POST"])
def addticket():
    guard = loggedInGuard()
    if guard is not None:
        return guard

    ticket_added = False

    connection = getDBconnection()
    try:
        resolvers = connection.execute(
            "SELECT username FROM users WHERE level = 1 ORDER BY username ASC"
        ).fetchall()

        if request.method == "GET":
            return render_template("addTicket.html", resolvers=resolvers)
        

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        resolver_username = request.form.get("resolver_username", "").strip()

        if not title or not description or not resolver_username:
            return render_template("addTicket.html", error="Title, description and resolver username are required")

        newRow = connection.execute(
            """
            INSERT INTO requests (request_title, username, request_body, resolver_username)
            VALUES (?, ?, ?, ?)
            """,
            (title, session.get("user"), description, resolver_username)
        )
        id = newRow.lastrowid
        ticket_added = True
        connection.commit()
        return redirect(url_for("main.tickets", message="Ticket created"))
    finally:
        connection.close()
        if ticket_added:
            detect_support_type(title, description, id)
            newAuditLog(session.get("user"), "ticket created")
   
@main.route("/removeticket", methods=["POST"])
def removeticket():
    request_id_raw = request.form.get("request_id", "").strip()
    if not request_id_raw.isdigit():
        return redirect(url_for("main.tickets", error="Invalid ticket id"))

    request_id = int(request_id_raw)
    guard = ownsTheTicketOrIsAdminGuard(request_id)
    if guard is not None:
        return guard
    
    # TODO: remove ticket
    return redirect(url_for("main.index"))

@main.route("/updateticket", methods=["POST"])
def updateticket():
    request_id_raw = request.form.get("request_id", "").strip()
    if not request_id_raw.isdigit():
        return redirect(url_for("main.tickets", error="Invalid ticket id"))

    request_id = int(request_id_raw)
    guard = ownsTheTicketOrIsAdminGuard(request_id)
    if guard is not None:
        return guard
    
    # TODO: update ticket
    return redirect(url_for("main.index"))