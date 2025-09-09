import random
from datetime import datetime, timedelta
from typing import List

import pandas as pd
from faker import Faker

from .db import connect, init_schema


def generate_mock_rows(num_rows: int = 120, seed: int = 42) -> pd.DataFrame:
    fake = Faker()
    Faker.seed(seed)
    random.seed(seed)

    rows: List[dict] = []

    base_campaigns = [
        ("Q3 Outreach", "Introducing our AI analytics"),
        ("Q3 Outreach", "Unlock insights with Coral Bricks"),
        ("Re-engagement", "We missed you—see what's new"),
        ("Re-engagement", "Quick question about your data stack"),
    ]

    # Date range: last 60 days
    now = datetime.utcnow()
    start_date = now - timedelta(days=60)

    for idx in range(num_rows):
        first_name = fake.first_name()
        last_name = fake.last_name()
        company = fake.company()
        domain = random.choice(["gmail.com", "outlook.com", "yahoo.com", "company.com", "proton.me"]) 
        local_part = f"{first_name}.{last_name}".lower().replace(" ", "")
        email_address = f"{local_part}@{domain}"

        campaign_name, subject = random.choice(base_campaigns)

        # Sent sometime in the last 60 days
        sent_at = fake.date_time_between(start_date=start_date, end_date=now)

        # Delivery and bounce behavior
        bounced = 1 if random.random() < 0.08 else 0
        delivered_at = None if bounced else sent_at + timedelta(minutes=random.randint(1, 120))

        # Open behavior
        opened_at = None
        if not bounced and random.random() < 0.52:
            opened_at = delivered_at + timedelta(minutes=random.randint(5, 1440)) if delivered_at else None

        # Reply behavior, conditional on open more likely
        replied_at = None
        reply_prob = 0.14 if opened_at else 0.04
        if not bounced and random.random() < reply_prob:
            base_time = opened_at or delivered_at or sent_at
            replied_at = base_time + timedelta(hours=random.randint(1, 72))

        rows.append(
            {
                "email_address": email_address,
                "first_name": first_name,
                "last_name": last_name,
                "company": company,
                "subject": subject,
                "campaign_name": campaign_name,
                "sent_at": sent_at.isoformat(),
                "delivered_at": delivered_at.isoformat() if delivered_at else None,
                "opened_at": opened_at.isoformat() if opened_at else None,
                "replied_at": replied_at.isoformat() if replied_at else None,
                "bounced": bounced,
            }
        )

    return pd.DataFrame(rows)


def seed_database(num_rows: int = 120) -> None:
    conn, _ = init_schema()
    df = generate_mock_rows(num_rows=num_rows)

    # Clear existing
    conn.execute("DELETE FROM email_events")
    conn.execute("DELETE FROM contacts")
    conn.commit()

    # Insert contacts first
    contacts = {}
    for r in df.itertuples(index=False):
        domain = r.email_address.split("@")[-1].lower()
        contacts[r.email_address] = (r.email_address, r.first_name, r.last_name, r.company, domain)
    conn.executemany(
        "INSERT OR REPLACE INTO contacts (email_address, first_name, last_name, company, domain) VALUES (?, ?, ?, ?, ?)",
        list(contacts.values()),
    )
    conn.commit()

    # Insert events with contact_id
    email_to_contact_id = {
        row[0]: row[1]
        for row in conn.execute("SELECT email_address, id FROM contacts").fetchall()
    }

    # Insert via executemany for speed
    conn.executemany(
        (
            "INSERT INTO email_events (email_address, first_name, last_name, company, subject, campaign_name, sent_at, delivered_at, opened_at, replied_at, bounced, contact_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        [
            (
                r.email_address,
                r.first_name,
                r.last_name,
                r.company,
                r.subject,
                r.campaign_name,
                r.sent_at,
                r.delivered_at,
                r.opened_at,
                r.replied_at,
                r.bounced,
                email_to_contact_id.get(r.email_address),
            )
            for r in df.itertuples(index=False)
        ],
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_database(140)


