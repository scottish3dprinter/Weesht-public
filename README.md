# Weesht

Weesht is a lightweight Flask-based internal helpdesk app for managing support tickets.

## Features

- User authentication (login/logout) with password hashing.
- Role-based access control:
  - **Admin (level `0`)** can view all tickets, manage users, and view audit logs.
  - **Resolver (level `1`)** can be assigned tickets and reply to ticket threads.
  - **User (level `2`)** can make tickets
- Tickets:
  - Create tickets.
  - View ticket list.
  - Open a ticket thread and post messages.
- Automatic SQLite database initialization with starter users.
- SMTP email support for welcome emails and password reset flows.
- Automatic assignment of tickets to the right team thourgh the use of classification.
  - AI classification for ticket routing to the correct department

## Tech Stack

- Python
- Flask
- SQLite
- Jinja2
- Docker

## Configuration

Configuration is loaded from environment variables in `config.py` (with defaults for local development).

| Variable | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | `dev-secret-key` | Flask session secret key. |
| `PORT` | `80` | Port used by `run.py`. |
| `SQLITE_DB_PATH` | `/data/weesht.db` | SQLite database file path. |
| `AUTO_REPLY_INTERVAL_SECONDS` | `120` | Polling interval for new messages. |
| `DEFAULT_ADMIN_USERNAME` | `admin` | Seed admin username created at DB init. |
| `DEFAULT_ADMIN_PASSWORD` | `password` | Seed admin password created at DB init. |
| `SMTP_PASS` | `""` | SMTP password used for outbound mail. |


## Docker

Build and run with Docker:

First SSH in to your VPS, install docker and clone this repository, then run the following.

```bash
mkdir ~/weeshtData
docker build -t weesht .
docker run --rm -p 8080:80 -v ~/weeshtData:/data\
  -e SECRET_KEY="replace-me" \
  -e DEFAULT_ADMIN_PASSWORD="replace-me" \
  -e SQLITE_DB_PATH="/data/weesht.db" \
  weesht
```

Then open `http://localhost:8080`.

## Email

Email requires outbound network access on specific ports not granted by default on VPS providers, you also need the SMTP environment variables to be set correctly.

## Automatic ticket classification

I use OpenAPI and send the ticket data and the possible categories, these will be contaned in a prompt asking the LLM what category works best and then it will email those resolvers and ask them to take over the ticket.

### Order of automatic classification

1. A new ticket is added with the default resolver this starts the automatic classification

2. The system makes an API call to a LLM that will analyse the title and description of the ticket aswell as the prompt from this software whitch asks the LLM to catagorise the ticket in to one of a few categories the prompt as asks the LLM to return in a specific format so we can easly extract the data from the response.

3. the ticket gets assinged that catagorie and is added to the approprit queue, an email can be sent to people with that responder type with the ticket data if they have opted in to email notifcations.

4. the ticket gets a response from one of the responders and can be marked close. the orginal maker of the ticket gets an email to say the ticket is closed.

### Categories

- `networking support`
- `user accounts`
- `package management support`
- `hardware support`
- `installation`
- `system performance support`
- `system settings`