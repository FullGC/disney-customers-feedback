#!/usr/bin/env python
"""Test script for Redis cache functionality."""
import redis
import json

# Test Redis connection
try:
    client = redis.Redis(host='localhost', port=6379, db=0)
    client.ping()
    print("✓ Redis connection successful!")
    
    # Test basic operations
    client.set('test_key', 'test_value')
    value = client.get('test_key')
    print(f"✓ Set/Get test: {value.decode('utf-8')}")
    
    # Test JSON storage
    test_data = {"question": "test", "answer": "response"}
    client.set('test_json', json.dumps(test_data))
    retrieved = json.loads(client.get('test_json'))
    print(f"✓ JSON storage test: {retrieved}")
    
    # Test TTL
    client.setex('test_ttl', 60, 'expires in 60 seconds')
    ttl = client.ttl('test_ttl')
    print(f"✓ TTL test: {ttl} seconds remaining")
    
    # Clean up
    client.delete('test_key', 'test_json', 'test_ttl')
    print("✓ Cleanup successful")
    
    # Get Redis info
    info = client.info('memory')
    print(f"\n📊 Redis Memory Usage: {info.get('used_memory_human', 'N/A')}")
    
    print("\n✅ All Redis tests passed!")
    
except redis.exceptions.ConnectionError as e:
    print(f"❌ Failed to connect to Redis: {e}")
    print("Make sure Redis is running: docker-compose up redis -d")
except Exception as e:
    print(f"❌ Error: {e}")
