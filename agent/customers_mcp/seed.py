"""Generates ~50 dummy customers and loads them into customers.db.

Run with (from agent/, so customers_mcp resolves as a package):
    uv run python -m customers_mcp.seed
"""

import random

from customers_mcp.database import get_connection, init_db

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Arun", "Priya", "Wei", "Mei", "Hiroshi",
    "Yuki", "Fatima", "Omar", "Carlos", "Sofia",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Kumar", "Sharma", "Chen", "Wang", "Tanaka", "Sato",
    "Khan", "Ali", "Silva", "Rossi",
]

CITIES_BY_COUNTRY = {
    "United States": ["New York", "San Francisco", "Chicago", "Austin"],
    "United Kingdom": ["London", "Manchester", "Bristol"],
    "India": ["Bengaluru", "Mumbai", "Delhi", "Chennai"],
    "Germany": ["Berlin", "Munich", "Hamburg"],
    "Japan": ["Tokyo", "Osaka", "Kyoto"],
    "Australia": ["Sydney", "Melbourne", "Brisbane"],
    "Canada": ["Toronto", "Vancouver", "Montreal"],
    "Brazil": ["Sao Paulo", "Rio de Janeiro"],
    "United Arab Emirates": ["Dubai", "Abu Dhabi"],
    "Singapore": ["Singapore"],
}


def _phone() -> str:
    return f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"


def generate_customers(count: int) -> list[tuple[str, str, str, str, str]]:
    customers = []
    countries = list(CITIES_BY_COUNTRY.keys())
    for i in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        country = random.choice(countries)
        city = random.choice(CITIES_BY_COUNTRY[country])
        customers.append((name, email, _phone(), city, country))
    return customers


def seed(count: int = 50, seed_value: int = 42) -> int:
    """Rebuild the table and insert `count` dummy customers. Returns the row count inserted."""
    random.seed(seed_value)
    init_db()
    customers = generate_customers(count)
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO customers (name, email, phone, city, country) VALUES (?, ?, ?, ?, ?)",
            customers,
        )
        conn.commit()
    return len(customers)


if __name__ == "__main__":
    inserted = seed()
    print(f"Seeded {inserted} customers into customers.db")
