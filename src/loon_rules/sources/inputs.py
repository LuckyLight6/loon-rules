"""Stable public entry point for source readers; implementations live in loon_rules.sources.formats."""
from loon_rules.sources.formats import extract_rows
from loon_rules.sources.formats.common import within, DestinationTables, LabelledLists, HeadingSectionText, PurposeFragments, product_host, https_product_host
from loon_rules.sources.formats.tables import host_table, endpoint_sets
from loon_rules.sources.formats.api import azure_cloud_metadata, sdk_client_endpoints, python_sdk_endpoints, code_examples, code_api_endpoints, curl_api_endpoints
from loon_rules.sources.formats.networks import labelled_networks, public_media_network
from loon_rules.sources.formats.documents import BrandRegionLinks
from loon_rules.sources.formats.feeds import http_provider_hosts
