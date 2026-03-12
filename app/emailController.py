import os
import smtplib
import socket
from email.message import EmailMessage
from .auditLog import newAuditLog

def send_email(to_email, subject, body):
    #newAuditLog("sys", f"sending email to {to_email}")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "weesht@arronweir.com"
    msg["To"] = to_email
    msg.set_content(body)

    host = "smtp.protonmail.ch"
    port = 587
    user = "weesht@arronweir.com"
    password = os.environ.get("SMTP_PASS") 

    if not password:
        #newAuditLog("sys", "failed to send email: SMTP_PASS not set")
        return False

    try:
        #newAuditLog("sys", f"smtp connect {host}:{port}")
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.set_debuglevel(0)
            #newAuditLog("sys", "smtp starttls")
            smtp.starttls()
            #newAuditLog("sys", "smtp login")
            smtp.login(user, password)
            #newAuditLog("sys", "smtp send_message")
            smtp.send_message(msg)

        #newAuditLog("sys", "email sent OK")
        return True

    except (smtplib.SMTPException, socket.timeout, OSError) as exc:
        #newAuditLog("sys", f"failed to send email: {type(exc).__name__}: {exc}")
        return False


def send_welcome_email(to_email, username):
    subject = "Welcome to Weesht"
    body = (
        f"Hi {username},\n\n"
        "Your Weesht account has been created, they should tell you your one time password.\n"
        "You can now log in.\n\n"
    )
    return send_email(to_email, subject, body)


def send_password_reset_email(to_email, username, temporary_password):
    subject = "Weesht Password Reset"
    body = (
        f"Hi {username},\n\n"
        "A temporary password was requested for your Weesht account.\n"
        f"Temporary password: {temporary_password}\n\n"
        "Please log in using this temporary password and set a new password from the update password page.\n"
    )
    return send_email(to_email, subject, body)

def send_ticket_update_email(to_email, username, ticket_id, update_message):
    subject = f"Weesht Ticket Update: {ticket_id}"
    body = (
        f"Hi {username},\n\n"
        f"Your ticket with ID {ticket_id} has been updated:\n\n"
        f"{update_message}\n\n"
        "Please log in to your Weesht account to view the update and respond if necessary.\n"
    )
    return send_email(to_email, subject, body)

def send_new_ticket_email(to_email, username, ticket_id, detected_support_type):
    subject = f"Weesht New Ticket: {ticket_id}"
    body = (
        f"Hi {username},\n\n"
        f"A new ticket with ID {ticket_id} and type {detected_support_type} has been created do you want to resolve it?\n\n"
        "Please log in to your Weesht account to view the ticket and respond if necessary.\n"
    )
    return send_email(to_email, subject, body)