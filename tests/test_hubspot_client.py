"""Smoke-test utils.hubspot_client against live HubSpot API."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingestion.config import load_settings
from utils.hubspot_client import get_all_objects

CONTACT_PROPERTIES = [
    "email",
    "firstname",
    "lastname",
    "company",
    "jobtitle",
    "lifecyclestage",
    "hs_lead_status",
    "createdate",
    "lastmodifieddate",
    "hubspot_owner_id",
]


def main() -> None:
    settings = load_settings()
    contacts = get_all_objects(
        settings.hubspot_token,
        "contacts",
        CONTACT_PROPERTIES,
    )

    print(f"Total contacts: {len(contacts)}")

    for contact in contacts[:5]:
        print(contact.get("id"), contact.get("properties"))


if __name__ == "__main__":
    main()
