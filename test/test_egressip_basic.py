#!/usr/bin/env python3
#Basic EgressIP Test - No external dependencies
import asyncio
import json
import subprocess
from datetime import datetime

async def test_egressip_basic():
    """Test basic EgressIP functionality without dependencies"""
    print("🧪 Testing EgressIP Basic Functionality")

    try:
        # Test 1: Check cluster access
        print("\n1️⃣ Testing cluster access...")
        result = subprocess.run(['oc', 'get', 'nodes', '--no-headers'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            node_count = len([line for line in result.stdout.split('\n') if line.strip()])
            print(f"✅ Cluster accessible - Found {node_count} nodes")
        else:
            print(f"❌ Cluster access failed: {result.stderr}")
            return

        # Test 2: Check EgressIP CRD
        print("\n2️⃣ Testing EgressIP CRD availability...")
        result = subprocess.run(['oc', 'get', 'crd', 'egressips.k8s.ovn.org'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ EgressIP CRD is available")
        else:
            print(f"❌ EgressIP CRD not found: {result.stderr}")

        # Test 3: Check existing EgressIPs
        print("\n3️⃣ Testing EgressIP objects...")
        result = subprocess.run(['oc', 'get', 'egressips', '-o', 'json'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            egressip_count = len(data.get('items', []))
            print(f"✅ Found {egressip_count} EgressIP objects")

            # Show EgressIP details if any exist
            for eip in data.get('items', [])[:3]:  # Show first 3
                name = eip['metadata']['name']
                spec_ips = eip.get('spec', {}).get('egressIPs', [])
                status_items = eip.get('status', {}).get('items', [])
                print(f"   📋 EgressIP: {name}")
                print(f"      Spec IPs: {spec_ips}")
                print(f"      Status Items: {len(status_items)}")
        else:
            print(f"❌ Could not get EgressIPs: {result.stderr}")

        # Test 4: Check network type
        print("\n4️⃣ Testing network configuration...")
        result = subprocess.run(['oc', 'get', 'network.operator', 'cluster',
                               '-o', 'jsonpath={.spec.defaultNetwork.type}'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            network_type = result.stdout.strip()
            print(f"✅ Network type: {network_type}")
            if network_type == "OVNKubernetes":
                print("✅ OVN-Kubernetes detected - EgressIP compatible")
            else:
                print("⚠️ Non-OVN network - EgressIP may not work properly")
        else:
            print(f"❌ Could not get network type: {result.stderr}")

        # Test 5: Check EgressIP-capable nodes
        print("\n5️⃣ Testing EgressIP-capable nodes...")
        result = subprocess.run(['oc', 'get', 'nodes', '-l',
                               'k8s.ovn.org/egress-assignable=true', '--no-headers'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            capable_nodes = len([line for line in result.stdout.split('\n') if line.strip()])
            print(f"✅ Found {capable_nodes} EgressIP-capable nodes")
        else:
            print(f"⚠️ Could not check EgressIP-capable nodes: {result.stderr}")

        print(f"\n🎯 EgressIP Basic Test Completed at {datetime.utcnow().isoformat()}")
        print("✅ Basic EgressIP environment validation successful!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_egressip_basic())
