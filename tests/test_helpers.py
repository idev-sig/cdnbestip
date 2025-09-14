"""
Test helper functions and utilities.
"""

import argparse


def create_test_args(**kwargs):
    """
    Create a test argparse.Namespace with all required attributes.

    Args:
        **kwargs: Override default values

    Returns:
        argparse.Namespace: Test arguments object
    """
    defaults = {
        # Core arguments
        "speed": 2.0,
        "port": None,
        "quantity": 0,
        "zone_type": "A",
        "url": None,
        "timeout": 600,
        # CloudFlare credentials
        "cloudflare_email": None,
        "cloudflare_api_key": None,
        "cloudflare_api_token": None,
        # DNS settings
        "domain": None,
        "prefix": None,
        "dns": False,
        "only": False,
        # Advanced options
        "cdn": None,
        "ipurl": None,
        "extend": None,
        "refresh": False,
        # Logging
        "log_level": "INFO",
        "debug": False,
        "verbose": False,
        "no_console_log": False,
        "no_file_log": False,
    }

    defaults.update(kwargs)
    return argparse.Namespace(**defaults)
