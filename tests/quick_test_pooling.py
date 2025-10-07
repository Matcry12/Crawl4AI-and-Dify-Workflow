#!/usr/bin/env python3
"""
Quick test to verify connection pooling is working

Run this after implementing connection pooling to verify it works.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.dify_api_resilient import ResilientDifyAPI
import logging

# Enable debug logging to see connection details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def quick_test():
    """Quick test to verify pooling works"""

    print("\n" + "="*60)
    print("🧪 QUICK CONNECTION POOLING TEST")
    print("="*60)

    # Test 1: Create API with pooling enabled
    print("\n✅ Test 1: Creating API with pooling enabled...")
    api = ResilientDifyAPI(
        base_url="http://localhost:8088",
        api_key="test-key",
        enable_connection_pooling=True
    )

    if api.session is not None:
        print("   ✓ Session created")
    else:
        print("   ✗ Session NOT created")
        return False

    if hasattr(api.session, 'headers'):
        print("   ✓ Headers configured")
    else:
        print("   ✗ Headers NOT configured")
        return False

    # Test 2: Create API with pooling disabled
    print("\n✅ Test 2: Creating API with pooling disabled...")
    api_no_pool = ResilientDifyAPI(
        base_url="http://localhost:8088",
        api_key="test-key",
        enable_connection_pooling=False
    )

    if api_no_pool.session is None:
        print("   ✓ Session correctly NOT created")
    else:
        print("   ✗ Session should be None")
        return False

    if hasattr(api_no_pool, 'headers'):
        print("   ✓ Headers fallback working")
    else:
        print("   ✗ Headers fallback NOT working")
        return False

    # Test 3: Check adapter configuration
    print("\n✅ Test 3: Checking adapter configuration...")
    if 'http://' in api.session.adapters:
        print("   ✓ HTTP adapter mounted")
    else:
        print("   ✗ HTTP adapter NOT mounted")
        return False

    if 'https://' in api.session.adapters:
        print("   ✓ HTTPS adapter mounted")
    else:
        print("   ✗ HTTPS adapter NOT mounted")
        return False

    # Test 4: Verify backward compatibility
    print("\n✅ Test 4: Testing backward compatibility...")
    api_default = ResilientDifyAPI(
        base_url="http://localhost:8088",
        api_key="test-key"
    )

    if api_default.enable_connection_pooling:
        print("   ✓ Pooling enabled by default")
    else:
        print("   ✗ Pooling should be enabled by default")
        return False

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\n🎉 Connection pooling is working correctly!")
    print("\nNext steps:")
    print("  1. Run unit tests: python tests/test_connection_pooling.py")
    print("  2. Run benchmark: python tests/benchmark_connection_pooling.py")
    print("="*60)

    return True


if __name__ == '__main__':
    success = quick_test()
    sys.exit(0 if success else 1)
