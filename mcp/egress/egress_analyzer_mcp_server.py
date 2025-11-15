#!/usr/bin/env python3
"""
OpenShift EgressIP Performance Analyzer MCP Server

This server provides AI-powered analysis and testing capabilities for OpenShift EgressIP functionality,
including large-scale performance testing, OVN rule validation, and automated bottleneck detection.

Author: Performance Scale Team
License: Apache-2.0
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastmcp import FastMCP

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from tools.egressip.corenet_6498_runner import CORENET6498Runner
    from tools.egressip.ovn_rule_analyzer import OVNRuleAnalyzer
    from tools.egressip.metrics_collector import EgressIPMetricsCollector
except ImportError as e:
    logging.error(f"Failed to import egress tools: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("EgressIP Performance Analyzer")

class EgressIPMCPServer:
    """MCP Server for EgressIP Performance Analysis"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or str(project_root / "config" / "config-egress.yml")
        self.config = self._load_config()
        
        # Initialize components
        self.test_runner = CORENET6498Runner()
        self.ovn_analyzer = OVNRuleAnalyzer()
        self.metrics_collector = EgressIPMetricsCollector()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"Config file not found: {self.config_path}. Using defaults.")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}. Using defaults.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "test_config": {
                "cornet_6498": {
                    "default_eip_objects": 10,
                    "default_pods_per_eip": 200,
                    "default_iterations": 20,
                    "default_timeout_minutes": 360
                }
            },
            "performance_thresholds": {
                "rule_validation": {
                    "max_snat_rules_per_node": 10000,
                    "rule_consistency_min_score": 0.8
                }
            }
        }

# Initialize server instance
server = EgressIPMCPServer()

@mcp.tool()
async def run_cornet_6498_test(
    eip_object_count: int = 10,
    pods_per_eip: int = 200,
    iterations: int = 20,
    ip_stack: str = "auto",
    platform: str = "auto"
) -> str:
    """
    Execute CORNET-6498 large-scale EgressIP stress test.
    
    This test creates multiple EgressIP objects with large numbers of pods and validates
    SNAT/LRP rules consistency under various stress conditions including node reboots,
    OVN pod restarts, and scaling operations.
    
    Args:
        eip_object_count: Number of EgressIP objects to create (default: 10)
        pods_per_eip: Number of pods per EgressIP object (default: 200)
        iterations: Number of test iterations per scenario (default: 20)
        ip_stack: IP stack type - auto, ipv4, ipv6, or dualstack (default: auto)
        platform: Target platform - auto, aws, gcp, azure, etc. (default: auto)
    
    Returns:
        JSON string containing test results, execution time, and analysis
    """
    try:
        config = {
            "eip_object_count": eip_object_count,
            "pods_per_eip": pods_per_eip,
            "iterations": iterations,
            "ip_stack": ip_stack,
            "platform": platform
        }
        
        result = await server.test_runner.run_test(config)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in run_cornet_6498_test: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, indent=2)


@mcp.tool()
async def validate_snat_lrp_rules(node_name: str) -> str:
    """
    Validate SNAT/LRP rules consistency on a specific OpenShift node.
    
    This tool examines the OVN database on the specified node to validate that
    SNAT and LRP (Logical Router Policy) rules are properly configured and
    consistent with the current EgressIP assignments.
    
    Args:
        node_name: Name of the OpenShift node to analyze
    
    Returns:
        JSON string containing rule counts, validation results, and any inconsistencies found
    """
    try:
        result = await server.ovn_analyzer.analyze_node_rules(node_name)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in validate_snat_lrp_rules: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "node_name": node_name,
            "timestamp": datetime.utcnow().isoformat()
        }, indent=2)


@mcp.tool()
async def analyze_egressip_performance(namespace: str = None) -> str:
    """
    Analyze EgressIP performance metrics and identify potential bottlenecks.
    
    This tool examines EgressIP objects, pod assignments, traffic patterns,
    and node resource utilization to identify performance issues and provide
    optimization recommendations.
    
    Args:
        namespace: Specific namespace to analyze (optional, analyzes all if not specified)
    
    Returns:
        JSON string containing performance analysis, bottleneck identification, and recommendations
    """
    try:
        result = await server.metrics_collector.collect_egressip_metrics()
        
        # Add performance analysis
        analysis_result = {
            "status": "success",
            "namespace": namespace,
            "metrics": result.get("metrics", []),
            "performance_insights": "Analysis completed - see metrics for details",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(analysis_result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in analyze_egressip_performance: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "namespace": namespace,
            "timestamp": datetime.utcnow().isoformat()
        }, indent=2)


@mcp.tool()
async def get_egressip_status() -> str:
    """
    Get comprehensive status of all EgressIP objects in the cluster.
    
    Returns detailed information about EgressIP objects including their current
    assignments, node distribution, and overall health status.
    
    Returns:
        JSON string containing EgressIP status information
    """
    try:
        result = await server.metrics_collector.collect_cluster_metrics()
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in get_egressip_status: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, indent=2)


@mcp.tool()
async def monitor_ovn_rules(node_name: str, duration_minutes: int = 5) -> str:
    """
    Monitor SNAT/LRP rule changes on a specific node over time.
    
    This tool continuously monitors OVN rule changes on the specified node
    to detect rule inconsistencies, missing rules, or unexpected changes.
    
    Args:
        node_name: Name of the OpenShift node to monitor
        duration_minutes: How long to monitor in minutes (default: 5)
    
    Returns:
        JSON string containing monitoring results and detected changes
    """
    try:
        duration_seconds = duration_minutes * 60
        result = await server.ovn_analyzer.monitor_rule_changes(node_name, duration_seconds)
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error in monitor_ovn_rules: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "node_name": node_name,
            "duration_minutes": duration_minutes,
            "timestamp": datetime.utcnow().isoformat()
        }, indent=2)


if __name__ == "__main__":
    # Start the MCP server
    logger.info("Starting EgressIP Performance Analyzer MCP Server")
    mcp.run(transport="stdio")