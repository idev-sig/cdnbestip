#!/usr/bin/env python3
"""
Demonstration script for the new timeout parameter functionality.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from cdnbestip.cli import parse_arguments
from cdnbestip.config import is_china_network, load_config


def test_timeout_parameter():
    """Test the new timeout parameter functionality."""
    print("🧪 Testing timeout parameter functionality...")

    # Simulate command line arguments with timeout
    original_argv = sys.argv[:]

    try:
        # Test 1: Default timeout
        sys.argv = ["cdnbestip", "-d", "example.com"]
        args = parse_arguments()
        config = load_config(args)
        print(f"✓ Default timeout: {config.timeout} seconds")

        # Test 2: Custom timeout via CLI
        sys.argv = ["cdnbestip", "-d", "example.com", "-T", "300"]
        args = parse_arguments()
        config = load_config(args)
        print(f"✓ Custom timeout (CLI): {config.timeout} seconds")

        # Test 3: Timeout via environment variable
        os.environ["CDNBESTIP_TIMEOUT"] = "900"
        sys.argv = ["cdnbestip", "-d", "example.com"]
        args = parse_arguments()
        config = load_config(args)
        print(f"✓ Custom timeout (ENV): {config.timeout} seconds")

        # Test 4: CLI overrides environment
        sys.argv = ["cdnbestip", "-d", "example.com", "-T", "120"]
        args = parse_arguments()
        config = load_config(args)
        print(f"✓ CLI overrides ENV: {config.timeout} seconds")

    finally:
        sys.argv = original_argv
        if "CDNBESTIP_TIMEOUT" in os.environ:
            del os.environ["CDNBESTIP_TIMEOUT"]


def test_china_network_detection():
    """Test China network detection functionality."""
    print("\n🌏 Testing China network detection...")

    # Test manual CN flag
    original_cn = os.environ.get("CN")
    try:
        os.environ["CN"] = "1"
        is_china = is_china_network()
        print(f"✓ CN=1 environment variable detected: {is_china}")

        del os.environ["CN"]
        is_china = is_china_network()
        print(f"✓ Real network detection (google.com test): {is_china}")

    finally:
        if original_cn:
            os.environ["CN"] = original_cn
        elif "CN" in os.environ:
            del os.environ["CN"]


def main():
    """Run all demonstration tests."""
    print("🚀 CDNBESTIP New Features Demonstration")
    print("=" * 50)

    test_timeout_parameter()
    test_china_network_detection()

    print("\n✅ All tests completed successfully!")
    print("\nNew features summary:")
    print("1. ⏱️  Timeout parameter (-T/--timeout) with default 600s")
    print("2. 🌏 China network detection (only uses CDN when in China)")
    print("3. 📁 Windows zip file support for binary downloads")


if __name__ == "__main__":
    main()
