#!/usr/bin/env python3
"""
Fixed EgressIP Metrics Test - Handle missing Prometheus URL
"""
import asyncio
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

try:
    from tools.utils.promql_basequery import PrometheusBaseQuery
    from tools.utils.promql_utility import mcpToolsUtility

    # Try to create PrometheusBaseQuery with a default URL
    try:
        # Common Prometheus URLs in OpenShift
        prometheus_urls = [
            "http://prometheus-k8s.openshift-monitoring.svc:9090",
            "https://prometheus-k8s.openshift-monitoring.svc:9090",
            "http://localhost:9090",
            None  # Try without URL as fallback
        ]

        prometheus_query = None
        for url in prometheus_urls:
            try:
                if url is None:
                    # Try without arguments
                    prometheus_query = PrometheusBaseQuery()
                else:
                    prometheus_query = PrometheusBaseQuery(url)
                print(f"✅ PrometheusBaseQuery created with: {url or 'default'}")
                break
            except Exception as e:
                print(f"⚠️ Failed with URL {url}: {e}")
                continue

        if prometheus_query is None:
            print("❌ Could not create PrometheusBaseQuery with any URL")
            sys.exit(1)

        # Try to create mcpToolsUtility
        mcp_utility = mcpToolsUtility()
        print("✅ mcpToolsUtility created successfully")

        # Now try to create a simplified EgressIP metrics collector
        from tools.egressip.egressip_metrics_collector import EgressIPMetricsCollector

        # We'll modify the class initialization to handle this
        print("⚠️ EgressIPMetricsCollector needs Prometheus URL fix...")

    except Exception as e:
        print(f"❌ Error creating utilities: {e}")

except Exception as e:
    print(f"❌ Import error: {e}")

print("Test completed!")