"""
etcd Node Health MCP Tool
Get node health metrics including PLEG relist latency for master nodes
"""

import logging
from datetime import datetime
from typing import Optional
import pytz

from .models import NodeHealthResponse, DurationInput

logger = logging.getLogger(__name__)


def register_node_health_tool(mcp, get_components_func):
    """Register the node health tool with the MCP server"""
    
    @mcp.tool()
    async def get_ocp_node_health(request: Optional[DurationInput] = None) -> NodeHealthResponse:
        """
        Get comprehensive node health metrics for all node groups (controlplane, infra, worker, workload).
        
        Monitors critical health indicators at the node level for all node groups:
        - PLEG (Pod Lifecycle Event Generator) relist P99 latency per node
        - PLEG performance patterns and health scoring
        - Node health status based on PLEG metrics
        - Cross-node PLEG latency comparison
        
        PLEG (Pod Lifecycle Event Generator) is a critical kubelet component that:
        - Monitors pod lifecycle state changes
        - Detects container state transitions
        - Reports pod status to the API server
        - Triggers pod sync operations
        
        PLEG relist latency metrics:
        - P99 latency: 99th percentile relist operation duration
        - Max latency: Maximum relist latency observed
        - Min latency: Minimum relist latency observed
        - Performance thresholds:
          * Normal: < 100ms (0.1s)
          * Warning: 100ms - 1000ms (0.1s - 1s)
          * Critical: > 1000ms (> 1s)
        
        High PLEG relist latency indicates:
        - Kubelet performance degradation
        - Slow pod lifecycle operations
        - Delayed pod status updates
        - Potential node stability issues
        - Container runtime problems
        
        Common causes of high PLEG latency:
        - High pod density on nodes
        - Container runtime performance issues
        - Disk I/O bottlenecks
        - CPU contention on nodes
        - Network storage latency
        - Large number of container state changes
        
        The tool queries all node groups (controlplane, infra, workload, worker) and returns
        results grouped by role. For worker nodes, the top 3 nodes by PLEG latency are returned
        to focus on nodes with the highest latency. If a specific node group has no nodes 
        or fails to collect, it will be marked with an error status but other groups will still be returned.
        
        Args:
            request: Optional request object with duration field. Default duration is '1h'.
                   Examples: '15m', '30m', '1h', '2h', '6h', '12h', '1d'
        
        Returns:
            ETCDNodeUsageResponse: Node health metrics including PLEG relist P99 latency, 
                                  max/min latency values, and health status for all node groups.
                                  Results are organized in a 'node_groups' dictionary with keys: 
                                  controlplane, infra, workload, worker.
                                  
        Use Cases:
            - Monitor kubelet health across all node groups
            - Identify nodes with degraded PLEG performance
            - Troubleshoot pod lifecycle operation delays
            - Detect node stability issues early
            - Capacity planning based on pod density limits
            - Performance baseline establishment
            - Post-upgrade health validation
            
        Example Response Structure:
            {
                "status": "success",
                "node_groups": {
                    "controlplane": {
                        "status": "success",
                        "total_nodes": 3,
                        "nodes": [
                            {"name": "master-0.example.com", "role": "controlplane"}
                        ],
                        "metrics": {
                            "p99_kubelet_pleg_relist_duration": {
                                "nodes": {
                                    "master-0.example.com": {
                                        "p99": 0.0125,
                                        "max": 0.0150,
                                        "min": 0.0100,
                                        "unit": "second"
                                    }
                                }
                            }
                        },
                        "top_nodes_by_pleg_latency": [
                            {
                                "rank": 1,
                                "node": "master-0.example.com",
                                "role": "controlplane",
                                "p99_latency": 0.0125,
                                "unit": "second"
                            }
                        ]
                    }
                }
            }
        """
        # Extract duration from request, default to "1h" if not provided
        duration = request.duration if request and request.duration else "1h"
        
        components = get_components_func()
        auth_manager = components.get('auth_manager')
        node_health_collector = components.get('node_health_collector')
        config = components.get('config')
        
        try:
            if not node_health_collector:
                # Lazy initialize
                if auth_manager is None:
                    from ocauth.openshift_auth import OpenShiftAuth
                    auth_manager = OpenShiftAuth(config.kubeconfig_path if config else None)
                    try:
                        await auth_manager.initialize()
                    except Exception:
                        return NodeHealthResponse(
                            status="error",
                            error="Failed to initialize OpenShift auth for node health",
                            timestamp=datetime.now(pytz.UTC).isoformat(),
                            duration=duration
                        )
                
                try:
                    from tools.node.node_health import nodeHealthCollector
                    prometheus_config = {
                        'url': auth_manager.prometheus_url,
                        'token': getattr(auth_manager, 'prometheus_token', None),
                        'verify_ssl': False
                    }
                    node_health_collector = nodeHealthCollector(auth_manager, prometheus_config)
                    components['node_health_collector'] = node_health_collector
                except Exception as e:
                    return NodeHealthResponse(
                        status="error",
                        error=f"Failed to initialize nodeHealthCollector: {e}",
                        timestamp=datetime.now(pytz.UTC).isoformat(),
                        duration=duration
                    )
            
            # Collect metrics for all node groups
            node_groups = {}
            overall_status = 'success'
            errors = []
            
            # Query each node group: controlplane (master), infra, workload, worker
            for node_group in ['controlplane', 'infra', 'workload', 'worker']:
                try:
                    # For worker nodes, return top 3 by PLEG latency
                    if node_group == 'worker':
                        group_result = await node_health_collector.collect_all_metrics(
                            node_group=node_group, 
                            duration=duration,
                            top_n_nodes=3
                        )
                    else:
                        group_result = await node_health_collector.collect_all_metrics(
                            node_group=node_group, 
                            duration=duration
                        )
                    
                    if group_result.get('status') == 'success':
                        node_groups[node_group] = group_result
                    else:
                        # Store error but don't fail the entire request
                        error_msg = group_result.get('error', 'Unknown error')
                        node_groups[node_group] = {
                            'status': 'error',
                            'error': error_msg
                        }
                        errors.append(f"{node_group}: {error_msg}")
                        logger.warning(f"Error collecting {node_group} node health: {error_msg}")
                except Exception as e:
                    # Store error but continue with other groups
                    error_msg = str(e)
                    node_groups[node_group] = {
                        'status': 'error',
                        'error': error_msg
                    }
                    errors.append(f"{node_group}: {error_msg}")
                    logger.error(f"Error collecting {node_group} node health: {e}")
            
            # Determine overall status
            successful_groups = [g for g, data in node_groups.items() if data.get('status') == 'success']
            if not successful_groups:
                overall_status = 'error'
            elif errors:
                overall_status = 'partial_success'
            
            # Build combined result
            combined_result = {
                'status': overall_status,
                'timestamp': datetime.now(pytz.UTC).isoformat(),
                'duration': duration,
                'category': 'node_health',
                'node_groups': node_groups,
                'health_summary': {
                    'total_node_groups': len(node_groups),
                    'successful_groups': len(successful_groups),
                    'failed_groups': len(errors),
                    'critical_nodes': _count_critical_nodes(node_groups),
                    'warning_nodes': _count_warning_nodes(node_groups),
                    'healthy_nodes': _count_healthy_nodes(node_groups)
                }
            }
            
            if errors:
                combined_result['errors'] = errors
            if overall_status == 'error':
                combined_result['error'] = 'Failed to collect health metrics for any node group'
            
            return NodeHealthResponse(
                status=overall_status,
                data=combined_result,
                error=combined_result.get('error'),
                timestamp=combined_result['timestamp'],
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"Error collecting node health metrics: {e}")
            return NodeHealthResponse(
                status="error",
                error=str(e),
                timestamp=datetime.now(pytz.UTC).isoformat(),
                duration=duration
            )


def _count_critical_nodes(node_groups):
    """Count nodes with critical PLEG latency (>1s)"""
    count = 0
    for group_data in node_groups.values():
        if group_data.get('status') != 'success':
            continue
        metrics = group_data.get('metrics', {})
        pleg_metrics = metrics.get('p99_kubelet_pleg_relist_duration', {})
        nodes = pleg_metrics.get('nodes', {})
        for node_data in nodes.values():
            p99 = node_data.get('p99', 0)
            if p99 > 1.0:  # Critical: > 1 second
                count += 1
    return count


def _count_warning_nodes(node_groups):
    """Count nodes with warning PLEG latency (0.1s - 1s)"""
    count = 0
    for group_data in node_groups.values():
        if group_data.get('status') != 'success':
            continue
        metrics = group_data.get('metrics', {})
        pleg_metrics = metrics.get('p99_kubelet_pleg_relist_duration', {})
        nodes = pleg_metrics.get('nodes', {})
        for node_data in nodes.values():
            p99 = node_data.get('p99', 0)
            if 0.1 < p99 <= 1.0:  # Warning: 0.1s - 1s
                count += 1
    return count


def _count_healthy_nodes(node_groups):
    """Count nodes with healthy PLEG latency (<0.1s)"""
    count = 0
    for group_data in node_groups.values():
        if group_data.get('status') != 'success':
            continue
        metrics = group_data.get('metrics', {})
        pleg_metrics = metrics.get('p99_kubelet_pleg_relist_duration', {})
        nodes = pleg_metrics.get('nodes', {})
        for node_data in nodes.values():
            p99 = node_data.get('p99', 0)
            if p99 <= 0.1:  # Healthy: <= 0.1 second
                count += 1
    return count