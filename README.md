# Gateway API

A Django REST API for gateway administrators, standalone website clients, customer accounts, invoices, payments, and transactions.

## Data model

- `User`: gateway administrator only, used by Django admin and admin API authentication.
- `Customer`: an account belonging to a client, with its own billing records.
- `Client`: standalone website identity with hashed credentials, email verification, and multiple customer accounts. It has no link to `User`.
- `ClientToken`: separate API token for a verified, active client.

- `Invoice`: amount billed to a customer, including line items and due/paid dates.
- `Payment`: an attempted or completed payment, optionally applied to an invoice.
- `Transaction`: an immutable-style financial event (charge, refund, or adjustment) tied optionally to a payment.

The client and customer relationship supports multiple accounts and preserves shared customer links from the previous profile model. Products are not implemented.

All domain IDs are UUIDs. Monetary amounts use fixed-precision decimals. JSON metadata fields allow provider-specific data without coupling the schema to one payment gateway.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Gateway admins get an API token with `POST /api/auth/token/` (or `/api/auth/admin/login/`) using `username` and `password`, then send `Authorization: Token <token>`.

Website clients use `POST /api/auth/login/` with `email` and `password`, then send `Authorization: ClientToken <token>`. `/api/auth/me/` returns the current client; `/api/auth/admin/me/` returns the current gateway admin.

Interactive API documentation is at `http://127.0.0.1:8000/api/docs/`; the OpenAPI schema is at `/api/schema/`.

## Endpoints

| Resource | Endpoint |
|---|---|
| Users | `/api/users/` |
| Customers | `/api/customers/` |
| Clients | `/api/clients/` |
| Invoices | `/api/invoices/` |
| Payments | `/api/payments/` |
| Transactions | `/api/transactions/` |

Gateway admins have CRUD access. Website clients can read their own identity and linked customer accounts and billing records. Clients can POST `/api/customers/` with `name` and `email` to create another account, automatically linked to themselves. They cannot choose an existing customer ID, access admin users, manage other clients, or write billing records. Other domain writes remain admin-only.

SQLite is configured for local development. For production, set a strong `DJANGO_SECRET_KEY`, disable `DJANGO_DEBUG`, configure allowed hosts, and switch `DATABASES` to PostgreSQL.

## Registration and account emails

Run `python manage.py migrate` before using the updated API. The new data migrations
copy legacy client-user credentials, verification status, and customer links into
standalone clients, then remove those ordinary client records from `User`.
Existing admin users remain. Client profiles retain their IDs and existing billing
records retain their customer IDs. Previously registered clients without profiles
receive a standalone client and first customer. Legacy client users with staff or
superuser privileges remain as gateway admins. Duplicate client emails differing
only by case must be resolved before migration.

The data migrations are intentionally irreversible: back up an existing database
before applying them. Old client API tokens and verification links no longer work;
clients must log in again and unverified clients must request a new email. Existing
password hashes are preserved. New website registration creates `Client` and its
first `Customer` together and never creates `User`. New clients must verify their
email before logging in. `is_active` stays true; `email_verified` starts false.

All endpoints below accept JSON using POST and allow unauthenticated requests:

| Endpoint | JSON body | Behavior |
|---|---|---|
| `/api/auth/register/` | `username`, `email`, `password`, optional `first_name`, `last_name`, `phone`, `customer_name` | Creates a standalone client and first customer; sends verification email; returns 201. |
| `/api/auth/verify-email/` | `token` | Verifies the email; returns 200. |
| `/api/auth/resend-verification/` | `email` | Sends another verification email if eligible. |
| `/api/auth/forgot-password/` | `email` | Sends a password-reset email for an active, verified account with a usable password. |
| `/api/auth/reset-password/` | `uid`, `token`, `new_password` | Changes the password and revokes existing API tokens. |

The first customer's name defaults to the client's username; supply `customer_name`
to choose it. Its email defaults to the client's registration email. Client creation
through the admin API uses the same flat credentials and creates a customer too.
Passwords must pass Django's configured validators. Public registration ignores
admin fields, activation flags, and supplied customer links. Website password-reset
and verification endpoints operate exclusively on `Client`, never admin users.
Forgot-password and resend requests return the same message for eligible and unknown
accounts. These endpoints and client login share a limit of 10 requests per hour per
IP using Django's cache. Configure a shared cache or gateway rate limiting for
multiple production workers.

Verification links expire after 24 hours and stop working after verification or
an email change. Password-reset links expire after one hour and stop working
after the password changes. Changing a client's email through the API sends a
new verification email and revokes its API token.

The default email backend prints emails in the server console; it does not
deliver to inboxes. To deliver real emails, set SMTP environment variables before
starting Django (replace the example values with your provider's settings):

```powershell
$env:EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
$env:EMAIL_HOST = "smtp.example.com"
$env:EMAIL_PORT = "587"
$env:EMAIL_HOST_USER = "your-smtp-user"
$env:EMAIL_HOST_PASSWORD = "your-smtp-password"
$env:EMAIL_USE_TLS = "true"
$env:EMAIL_USE_SSL = "false"
$env:DEFAULT_FROM_EMAIL = "Gateway <noreply@your-domain.com>"
$env:EMAIL_VERIFICATION_URL = "https://your-frontend.example/verify-email"
$env:PASSWORD_RESET_URL = "https://your-frontend.example/reset-password"
```

For implicit TLS on port 465, use `EMAIL_USE_SSL=true` and `EMAIL_USE_TLS=false`.
Do not commit SMTP credentials. Environment variables are read directly; this
project does not automatically load `.env` files.

Email links point to frontend pages. Those pages must read query parameters and
POST them to the matching API: verification links contain `token`; reset links
contain `uid` and `token`, which the page submits alongside `new_password`.
This repository has no frontend pages; the default links point to
`http://localhost:3000/verify-email` and `http://localhost:3000/reset-password`.
You can also copy those parameters into the API docs to test the flow.

Optional settings: `EMAIL_VERIFICATION_TIMEOUT` (seconds, default 86400) and
`PASSWORD_RESET_TIMEOUT` (seconds, default 3600). Registration returns 503 and
rolls back both the client and customer if SMTP delivery fails; resend and forgot-password log
delivery failures while keeping their responses generic. SMTP acceptance does
not guarantee inbox delivery; check your provider's delivery logs.
