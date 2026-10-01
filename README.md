# Gateway API

A Django REST API for administrative users, customers, client-site users, invoices, payments, and transactions.

## Data model

- `User`: authentication record with `admin` or `client` role. Admin-role users manage the API.
- `Customer`: the billed organization or account.
- `Client`: one-to-one profile for a client-role user, linked to a customer.
- `Invoice`: amount billed to a customer, including line items and due/paid dates.
- `Payment`: an attempted or completed payment, optionally applied to an invoice.
- `Transaction`: an immutable-style financial event (charge, refund, or adjustment) tied optionally to a payment.

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

Get an API token with `POST /api/auth/token/` using `username` and `password`, then send it as `Authorization: Token <token>`.

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

Admin-role users have CRUD access. Client-role users have read-only access to their own profile, customer, and that customer's billing records. Django superusers are also treated as admins.

SQLite is configured for local development. For production, set a strong `DJANGO_SECRET_KEY`, disable `DJANGO_DEBUG`, configure allowed hosts, and switch `DATABASES` to PostgreSQL.

## Registration and account emails

Apply the new migration with `python manage.py migrate`. Existing accounts remain
verified. Newly registered clients and clients created through the admin API must
verify their email before using `/api/auth/login/` or `/api/auth/token/`.

All endpoints below accept JSON using POST and allow unauthenticated requests:

| Endpoint | JSON body | Behavior |
|---|---|---|
| `/api/auth/register/` | `username`, `email`, `password`, optional `first_name`, `last_name` | Creates a client-role user and sends verification email; returns 201. |
| `/api/auth/verify-email/` | `token` | Verifies the email; returns 200. |
| `/api/auth/resend-verification/` | `email` | Sends another verification email if eligible. |
| `/api/auth/forgot-password/` | `email` | Sends a password-reset email for an active, verified account with a usable password. |
| `/api/auth/reset-password/` | `uid`, `token`, `new_password` | Changes the password and revokes existing API tokens. |

Public registration creates an authentication record. An admin must create its
`Client` profile in Django admin (`/admin/`), selecting the registered user and
the appropriate customer. `/api/clients/` creates a new user with its profile;
use Django admin to link an already registered user. Public users
cannot choose a role or access an existing customer's billing data. Passwords
must pass Django's configured password validators. Forgot-password and resend
requests return the same message for eligible and unknown accounts. These
endpoints share a limit of 10 requests per hour per IP using Django's cache.
Configure a shared cache or gateway rate limiting for multiple production workers.

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
rolls back the account if SMTP delivery fails; resend and forgot-password log
delivery failures while keeping their responses generic. SMTP acceptance does
not guarantee inbox delivery; check your provider's delivery logs.
