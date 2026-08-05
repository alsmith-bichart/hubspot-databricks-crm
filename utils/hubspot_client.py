"""Compatibility re-export — prefer ingestion.hubspot_client."""

from ingestion.hubspot_client import (  # noqa: F401
    HubSpotError,
    get_all_objects,
    get_all_owners,
    get_associations_batch,
    get_deal_pipelines,
    get_page,
)
