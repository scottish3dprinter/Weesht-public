from .db import getDBconnection

def newAuditLog(username, action):
    connection = getDBconnection()
    try:
        connection.execute(
            "INSERT INTO audit_logs (username, action) VALUES (?, ?)",
            (username, action)
        )
        connection.commit()
    finally:
        connection.close()