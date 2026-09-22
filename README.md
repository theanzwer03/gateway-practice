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
