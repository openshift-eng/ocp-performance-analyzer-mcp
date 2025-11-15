#!/usr/bin/env python3
"""
EgressIP Metrics Collector

This module collects, processes, and stores EgressIP-related performance metrics
for long-term analysis and trend identification.
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

logger = logging.getLogger(__name__)

class EgressIPMetricsCollector:
    """Collector for EgressIP performance and operational metrics"""
    
    def __init__(self, database_path: str = "./metrics/egressip_metrics.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for metrics storage"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create tables for different metric types
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egressip_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        egressip_name TEXT NOT NULL,
                        namespace TEXT,
                        status TEXT,
                        assigned_node TEXT,
                        assigned_ip TEXT,
                        pod_count INTEGER,
                        metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ovn_rule_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        node_name TEXT NOT NULL,
                        snat_rules_count INTEGER,
                        lrp_rules_count INTEGER,
                        parsing_errors INTEGER,
                        consistency_score REAL,
                        metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_tests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        test_name TEXT NOT NULL,
                        test_config_json TEXT,
                        execution_time_seconds REAL,
                        test_passed BOOLEAN,
                        scenarios_completed INTEGER,
                        total_scenarios INTEGER,
                        metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cluster_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        total_nodes INTEGER,
                        egress_capable_nodes INTEGER,
                        total_egressips INTEGER,
                        total_pods_with_egressip INTEGER,
                        network_type TEXT,
                        metrics_json TEXT
                    )
                """)
                
                # Create indices for better query performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_timestamp ON egressip_status(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ovn_timestamp ON ovn_rule_metrics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON performance_tests(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster_timestamp ON cluster_metrics(timestamp)")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def collect_egressip_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive EgressIP metrics"""
        try:
            logger.info("Collecting EgressIP metrics")
            
            # Get all EgressIP objects
            egressips = await self._get_egressip_objects()
            
            # Get pod assignments
            pod_assignments = await self._get_pod_egressip_assignments()
            
            # Process each EgressIP object
            metrics = []
            for egressip in egressips:
                egressip_metric = await self._process_egressip_object(egressip, pod_assignments)
                metrics.append(egressip_metric)
            
            # Store metrics in database
            timestamp = datetime.utcnow().isoformat()
            for metric in metrics:
                await self._store_egressip_metric(timestamp, metric)
            
            return {
                "status": "success",
                "timestamp": timestamp,
                "metrics_collected": len(metrics),
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP metrics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def collect_ovn_rule_metrics(self, node_names: List[str]) -> Dict[str, Any]:
        """Collect OVN rule metrics from specified nodes"""
        try:
            logger.info(f"Collecting OVN rule metrics from {len(node_names)} nodes")
            
            metrics = []
            timestamp = datetime.utcnow().isoformat()
            
            for node_name in node_names:
                node_metric = await self._collect_node_ovn_metrics(node_name)
                node_metric["node_name"] = node_name
                node_metric["timestamp"] = timestamp
                metrics.append(node_metric)
                
                # Store in database
                await self._store_ovn_rule_metric(timestamp, node_metric)
            
            return {
                "status": "success",
                "timestamp": timestamp,
                "nodes_analyzed": len(node_names),
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Error collecting OVN rule metrics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def collect_cluster_metrics(self) -> Dict[str, Any]:
        """Collect cluster-wide EgressIP metrics"""
        try:
            logger.info("Collecting cluster-wide metrics")
            
            # Get cluster information
            cluster_info = await self._get_cluster_info()
            
            # Get network configuration
            network_info = await self._get_network_info()
            
            # Count EgressIP-related resources
            egressip_count = await self._count_egressip_objects()
            pod_count = await self._count_pods_with_egressip()
            
            timestamp = datetime.utcnow().isoformat()
            metrics = {
                "timestamp": timestamp,
                "total_nodes": cluster_info.get("node_count", 0),
                "egress_capable_nodes": cluster_info.get("egress_capable_nodes", 0),
                "total_egressips": egressip_count,
                "total_pods_with_egressip": pod_count,
                "network_type": network_info.get("network_type", "unknown"),
                "cluster_info": cluster_info,
                "network_info": network_info
            }
            
            # Store in database
            await self._store_cluster_metric(timestamp, metrics)
            
            return {
                "status": "success",
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Error collecting cluster metrics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def store_performance_test_result(self, test_name: str, config: Dict[str, Any], results: Dict[str, Any]) -> bool:
        """Store performance test results in database"""
        try:
            timestamp = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO performance_tests 
                    (timestamp, test_name, test_config_json, execution_time_seconds, 
                     test_passed, scenarios_completed, total_scenarios, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    test_name,
                    json.dumps(config),
                    results.get("execution_time", 0),
                    results.get("test_passed", False),
                    results.get("scenarios_completed", 0),
                    results.get("total_scenarios", 0),
                    json.dumps(results)
                ))
                conn.commit()
            
            logger.info(f"Stored performance test result: {test_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing performance test result: {e}")
            return False
    
    async def get_metrics_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get summary of metrics from the last N hours"""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # EgressIP metrics summary
                cursor.execute("""
                    SELECT COUNT(*) as total_records,
                           COUNT(DISTINCT egressip_name) as unique_egressips,
                           AVG(pod_count) as avg_pod_count
                    FROM egressip_status 
                    WHERE timestamp > ?
                """, (cutoff_time,))
                egressip_summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
                
                # OVN rule metrics summary
                cursor.execute("""
                    SELECT COUNT(*) as total_records,
                           COUNT(DISTINCT node_name) as unique_nodes,
                           AVG(snat_rules_count) as avg_snat_rules,
                           AVG(lrp_rules_count) as avg_lrp_rules,
                           AVG(consistency_score) as avg_consistency_score
                    FROM ovn_rule_metrics 
                    WHERE timestamp > ?
                """, (cutoff_time,))
                ovn_summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
                
                # Performance test summary
                cursor.execute("""
                    SELECT COUNT(*) as total_tests,
                           COUNT(CASE WHEN test_passed = 1 THEN 1 END) as passed_tests,
                           AVG(execution_time_seconds) as avg_execution_time
                    FROM performance_tests 
                    WHERE timestamp > ?
                """, (cutoff_time,))
                perf_summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
                
                # Recent cluster metrics
                cursor.execute("""
                    SELECT * FROM cluster_metrics 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (cutoff_time,))
                cluster_result = cursor.fetchone()
                cluster_summary = {}
                if cluster_result:
                    cluster_summary = dict(zip([col[0] for col in cursor.description], cluster_result))
                
                return {
                    "status": "success",
                    "time_range_hours": hours_back,
                    "cutoff_time": cutoff_time,
                    "egressip_metrics": egressip_summary,
                    "ovn_rule_metrics": ovn_summary,
                    "performance_tests": perf_summary,
                    "latest_cluster_metrics": cluster_summary
                }
                
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_trend_analysis(self, metric_type: str, days_back: int = 7) -> Dict[str, Any]:
        """Analyze trends in metrics over time"""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                if metric_type == "egressip_status":
                    cursor.execute("""
                        SELECT DATE(timestamp) as date,
                               COUNT(DISTINCT egressip_name) as unique_egressips,
                               AVG(pod_count) as avg_pod_count,
                               COUNT(*) as total_records
                        FROM egressip_status 
                        WHERE timestamp > ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date
                    """, (cutoff_time,))
                    
                elif metric_type == "ovn_rules":
                    cursor.execute("""
                        SELECT DATE(timestamp) as date,
                               AVG(snat_rules_count) as avg_snat_rules,
                               AVG(lrp_rules_count) as avg_lrp_rules,
                               AVG(consistency_score) as avg_consistency,
                               COUNT(*) as total_records
                        FROM ovn_rule_metrics 
                        WHERE timestamp > ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date
                    """, (cutoff_time,))
                    
                elif metric_type == "performance_tests":
                    cursor.execute("""
                        SELECT DATE(timestamp) as date,
                               COUNT(*) as total_tests,
                               COUNT(CASE WHEN test_passed = 1 THEN 1 END) as passed_tests,
                               AVG(execution_time_seconds) as avg_execution_time
                        FROM performance_tests 
                        WHERE timestamp > ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date
                    """, (cutoff_time,))
                
                else:
                    return {
                        "status": "error",
                        "error": f"Unknown metric type: {metric_type}"
                    }
                
                results = cursor.fetchall()
                columns = [col[0] for col in cursor.description]
                
                trend_data = []
                for row in results:
                    trend_data.append(dict(zip(columns, row)))
                
                # Calculate trend indicators
                trend_analysis = self._calculate_trends(trend_data, metric_type)
                
                return {
                    "status": "success",
                    "metric_type": metric_type,
                    "days_analyzed": days_back,
                    "data_points": len(trend_data),
                    "trend_data": trend_data,
                    "trend_analysis": trend_analysis
                }
                
        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _calculate_trends(self, data: List[Dict[str, Any]], metric_type: str) -> Dict[str, Any]:
        """Calculate trend indicators from time series data"""
        if len(data) < 2:
            return {"trend": "insufficient_data", "details": "Need at least 2 data points"}
        
        try:
            if metric_type == "egressip_status":
                # Analyze EgressIP trends
                egressip_counts = [d.get("unique_egressips", 0) for d in data]
                pod_counts = [d.get("avg_pod_count", 0) for d in data if d.get("avg_pod_count") is not None]
                
                return {
                    "egressip_trend": self._simple_trend(egressip_counts),
                    "pod_count_trend": self._simple_trend(pod_counts) if pod_counts else "no_data",
                    "latest_values": {
                        "unique_egressips": egressip_counts[-1] if egressip_counts else 0,
                        "avg_pod_count": pod_counts[-1] if pod_counts else 0
                    }
                }
                
            elif metric_type == "ovn_rules":
                # Analyze OVN rule trends
                snat_counts = [d.get("avg_snat_rules", 0) for d in data if d.get("avg_snat_rules") is not None]
                lrp_counts = [d.get("avg_lrp_rules", 0) for d in data if d.get("avg_lrp_rules") is not None]
                consistency_scores = [d.get("avg_consistency", 0) for d in data if d.get("avg_consistency") is not None]
                
                return {
                    "snat_rules_trend": self._simple_trend(snat_counts) if snat_counts else "no_data",
                    "lrp_rules_trend": self._simple_trend(lrp_counts) if lrp_counts else "no_data",
                    "consistency_trend": self._simple_trend(consistency_scores) if consistency_scores else "no_data"
                }
                
            elif metric_type == "performance_tests":
                # Analyze performance test trends
                execution_times = [d.get("avg_execution_time", 0) for d in data if d.get("avg_execution_time") is not None]
                pass_rates = []
                
                for d in data:
                    total = d.get("total_tests", 0)
                    passed = d.get("passed_tests", 0)
                    if total > 0:
                        pass_rates.append(passed / total)
                
                return {
                    "execution_time_trend": self._simple_trend(execution_times) if execution_times else "no_data",
                    "pass_rate_trend": self._simple_trend(pass_rates) if pass_rates else "no_data"
                }
            
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            return {"trend": "calculation_error", "error": str(e)}
        
        return {"trend": "unknown"}
    
    def _simple_trend(self, values: List[float]) -> str:
        """Calculate simple trend direction from a list of values"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Calculate average of first half vs second half
        mid_point = len(values) // 2
        first_half_avg = sum(values[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(values[mid_point:]) / (len(values) - mid_point)
        
        diff_percent = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        if diff_percent > 10:
            return "increasing"
        elif diff_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    # Helper methods for data collection
    
    async def _get_egressip_objects(self) -> List[Dict[str, Any]]:
        """Get all EgressIP objects from cluster"""
        try:
            cmd = ['oc', 'get', 'egressips', '-o', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                return data.get('items', [])
            else:
                logger.error(f"Error getting EgressIP objects: {stderr.decode()}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting EgressIP objects: {e}")
            return []
    
    async def _get_pod_egressip_assignments(self) -> Dict[str, List[str]]:
        """Get pods assigned to each EgressIP"""
        # This would require more complex logic to map pods to EgressIPs
        # For now, return empty dict
        return {}
    
    async def _process_egressip_object(self, egressip: Dict[str, Any], pod_assignments: Dict[str, List[str]]) -> Dict[str, Any]:
        """Process individual EgressIP object to extract metrics"""
        try:
            name = egressip['metadata']['name']
            namespace = egressip['metadata'].get('namespace', 'cluster-wide')
            
            spec = egressip.get('spec', {})
            status = egressip.get('status', {})
            
            # Extract key metrics
            metrics = {
                "name": name,
                "namespace": namespace,
                "spec_egressips": spec.get('egressIPs', []),
                "status_items": status.get('items', []),
                "pod_count": len(pod_assignments.get(name, [])),
                "assigned_nodes": list(set(item.get('node', '') for item in status.get('items', []) if item.get('node'))),
                "assigned_ips": list(set(item.get('egressIP', '') for item in status.get('items', []) if item.get('egressIP')))
            }
            
            # Determine overall status
            if len(metrics["status_items"]) == len(metrics["spec_egressips"]):
                metrics["status"] = "ready"
            elif len(metrics["status_items"]) > 0:
                metrics["status"] = "partial"
            else:
                metrics["status"] = "pending"
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error processing EgressIP object: {e}")
            return {"name": "unknown", "error": str(e)}
    
    async def _store_egressip_metric(self, timestamp: str, metric: Dict[str, Any]):
        """Store EgressIP metric in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO egressip_status 
                    (timestamp, egressip_name, namespace, status, assigned_node, assigned_ip, pod_count, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    metric.get("name", ""),
                    metric.get("namespace", ""),
                    metric.get("status", "unknown"),
                    ",".join(metric.get("assigned_nodes", [])),
                    ",".join(metric.get("assigned_ips", [])),
                    metric.get("pod_count", 0),
                    json.dumps(metric)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing EgressIP metric: {e}")

    async def _collect_node_ovn_metrics(self, node_name: str) -> Dict[str, Any]:
        """Collect OVN metrics for a specific node"""
        # This would use the OVN analyzer we created earlier
        from .ovn_rule_analyzer import OVNRuleAnalyzer
        
        analyzer = OVNRuleAnalyzer()
        result = await analyzer.analyze_node_rules(node_name)
        
        if result["status"] == "success":
            return {
                "snat_rules_count": result["rule_counts"]["snat_rules"],
                "lrp_rules_count": result["rule_counts"]["lrp_rules"],
                "parsing_errors": len(result["snat_analysis"]["potential_issues"]) + len(result["lrp_analysis"]["potential_issues"]),
                "consistency_score": result["consistency_check"].get("consistency_score", 0.0)
            }
        else:
            return {
                "snat_rules_count": 0,
                "lrp_rules_count": 0,
                "parsing_errors": 1,
                "consistency_score": 0.0,
                "error": result.get("error", "Unknown error")
            }

    async def _store_ovn_rule_metric(self, timestamp: str, metric: Dict[str, Any]):
        """Store OVN rule metric in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO ovn_rule_metrics 
                    (timestamp, node_name, snat_rules_count, lrp_rules_count, parsing_errors, consistency_score, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    metric.get("node_name", ""),
                    metric.get("snat_rules_count", 0),
                    metric.get("lrp_rules_count", 0),
                    metric.get("parsing_errors", 0),
                    metric.get("consistency_score", 0.0),
                    json.dumps(metric)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing OVN rule metric: {e}")

    async def _get_cluster_info(self) -> Dict[str, Any]:
        """Get basic cluster information"""
        try:
            # Get total node count
            cmd = ['oc', 'get', 'nodes', '--no-headers']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            node_count = len(stdout.decode().strip().split('\n')) if stdout else 0
            
            # Get egress-capable nodes
            cmd = ['oc', 'get', 'nodes', '-l', 'k8s.ovn.org/egress-assignable=true', '--no-headers']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            egress_capable_nodes = len(stdout.decode().strip().split('\n')) if stdout and stdout.strip() else 0
            
            return {
                "node_count": node_count,
                "egress_capable_nodes": egress_capable_nodes
            }
            
        except Exception as e:
            logger.error(f"Error getting cluster info: {e}")
            return {"node_count": 0, "egress_capable_nodes": 0}

    async def _get_network_info(self) -> Dict[str, Any]:
        """Get cluster network configuration"""
        try:
            cmd = ['oc', 'get', 'network.operator', 'cluster', '-o', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                network_type = data.get('spec', {}).get('defaultNetwork', {}).get('type', 'unknown')
                return {"network_type": network_type}
            
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
        
        return {"network_type": "unknown"}

    async def _count_egressip_objects(self) -> int:
        """Count total EgressIP objects"""
        try:
            cmd = ['oc', 'get', 'egressips', '--no-headers']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return len(stdout.decode().strip().split('\n')) if stdout and stdout.strip() else 0
            
        except Exception as e:
            logger.error(f"Error counting EgressIP objects: {e}")
            return 0

    async def _count_pods_with_egressip(self) -> int:
        """Count pods that have EgressIP assignments"""
        # This would require complex label/namespace matching
        # For now, return 0 - would need full implementation
        return 0

    async def _store_cluster_metric(self, timestamp: str, metrics: Dict[str, Any]):
        """Store cluster metric in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO cluster_metrics 
                    (timestamp, total_nodes, egress_capable_nodes, total_egressips, 
                     total_pods_with_egressip, network_type, metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    metrics.get("total_nodes", 0),
                    metrics.get("egress_capable_nodes", 0),
                    metrics.get("total_egressips", 0),
                    metrics.get("total_pods_with_egressip", 0),
                    metrics.get("network_type", "unknown"),
                    json.dumps(metrics)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing cluster metric: {e}")


async def main():
    """Main function for standalone testing"""
    collector = EgressIPMetricsCollector()
    
    # Test metrics collection
    result = await collector.collect_cluster_metrics()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())