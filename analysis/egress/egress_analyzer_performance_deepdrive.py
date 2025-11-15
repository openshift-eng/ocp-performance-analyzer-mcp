#!/usr/bin/env python3
"""
EgressIP Performance Deep Dive Analysis

This module provides comprehensive deep-dive performance analysis for OpenShift EgressIP
functionality, including bottleneck identification, performance pattern analysis, and
optimization recommendations.

Author: Performance Scale Team
License: Apache-2.0
"""

import asyncio
import json
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Represents a performance metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    labels: Dict[str, str] = None

@dataclass
class PerformanceInsight:
    """Represents a performance analysis insight"""
    category: str
    severity: str  # "info", "warning", "critical"
    title: str
    description: str
    recommendations: List[str]
    affected_resources: List[str] = None

class EgressIPPerformanceDeepDive:
    """Deep dive performance analyzer for EgressIP functionality"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.performance_thresholds = self.config.get('performance_thresholds', {})
        
    async def analyze_test_performance(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform deep analysis of CORNET-6498 test performance results
        
        Args:
            test_results: Results from CORNET-6498 test execution
            
        Returns:
            Comprehensive performance analysis with insights and recommendations
        """
        try:
            logger.info("Starting deep dive performance analysis")
            
            analysis = {
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "test_summary": self._analyze_test_summary(test_results),
                "performance_patterns": await self._analyze_performance_patterns(test_results),
                "bottleneck_analysis": await self._identify_bottlenecks(test_results),
                "resource_utilization": await self._analyze_resource_utilization(test_results),
                "scaling_analysis": await self._analyze_scaling_behavior(test_results),
                "recommendations": await self._generate_optimization_recommendations(test_results),
                "insights": []
            }
            
            # Generate insights based on analysis
            analysis["insights"] = await self._generate_performance_insights(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in deep dive performance analysis: {e}")
            return {
                "status": "error",
                "error": str(e),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
    
    def _analyze_test_summary(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze overall test execution summary"""
        try:
            execution_summary = test_results.get("execution_summary", {})
            test_results_data = test_results.get("test_results", {})
            
            summary = {
                "overall_status": execution_summary.get("status", "unknown"),
                "total_execution_time": execution_summary.get("execution_time_seconds", 0),
                "scenarios_completed": 0,
                "scenarios_total": 4,  # CORNET-6498 has 4 standard scenarios
                "success_rate": 0.0,
                "performance_score": 0.0
            }
            
            # Calculate scenarios completion
            scenarios = test_results_data.get("scenarios", {})
            completed_scenarios = sum(1 for scenario in scenarios.values() if scenario.get("passed", False))
            summary["scenarios_completed"] = completed_scenarios
            summary["success_rate"] = completed_scenarios / summary["scenarios_total"] if summary["scenarios_total"] > 0 else 0
            
            # Calculate performance score (0-100)
            performance_factors = []
            
            # Factor 1: Success rate (40% weight)
            performance_factors.append(summary["success_rate"] * 40)
            
            # Factor 2: Execution time efficiency (30% weight)
            expected_max_time = self.performance_thresholds.get("test_execution", {}).get("cornet_6498_max_hours", 6) * 3600
            time_efficiency = max(0, 1 - (summary["total_execution_time"] / expected_max_time)) if expected_max_time > 0 else 0
            performance_factors.append(time_efficiency * 30)
            
            # Factor 3: Resource efficiency (30% weight)
            # This would be calculated based on resource utilization data
            performance_factors.append(25)  # Placeholder
            
            summary["performance_score"] = sum(performance_factors)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error analyzing test summary: {e}")
            return {"error": str(e)}
    
    async def _analyze_performance_patterns(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance patterns across test scenarios"""
        try:
            patterns = {
                "scenario_performance": {},
                "timing_patterns": {},
                "consistency_patterns": {},
                "degradation_patterns": []
            }
            
            scenarios = test_results.get("test_results", {}).get("scenarios", {})
            
            # Analyze each scenario's performance
            for scenario_name, scenario_data in scenarios.items():
                scenario_analysis = {
                    "average_iteration_time": 0,
                    "consistency_score": 0,
                    "performance_trend": "stable",
                    "outliers": []
                }
                
                # Calculate timing metrics if available
                iterations = scenario_data.get("iterations_completed", 0)
                if iterations > 0:
                    # Estimate iteration time
                    total_time = test_results.get("execution_summary", {}).get("execution_time_seconds", 0)
                    scenario_analysis["average_iteration_time"] = total_time / (len(scenarios) * iterations)
                
                patterns["scenario_performance"][scenario_name] = scenario_analysis
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing performance patterns: {e}")
            return {"error": str(e)}
    
    async def _identify_bottlenecks(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Identify performance bottlenecks from test results"""
        try:
            bottlenecks = {
                "identified_bottlenecks": [],
                "potential_bottlenecks": [],
                "bottleneck_categories": {
                    "network": [],
                    "compute": [],
                    "storage": [],
                    "ovn": []
                }
            }
            
            # Analyze execution time for bottlenecks
            execution_time = test_results.get("execution_summary", {}).get("execution_time_seconds", 0)
            max_expected_time = self.performance_thresholds.get("test_execution", {}).get("cornet_6498_max_hours", 6) * 3600
            
            if execution_time > max_expected_time:
                bottlenecks["identified_bottlenecks"].append({
                    "type": "execution_time",
                    "severity": "high",
                    "description": f"Test execution time ({execution_time}s) exceeded threshold ({max_expected_time}s)",
                    "category": "compute"
                })
            
            # Analyze scenario failures for bottlenecks
            scenarios = test_results.get("test_results", {}).get("scenarios", {})
            failed_scenarios = [name for name, data in scenarios.items() if not data.get("passed", False)]
            
            for scenario_name in failed_scenarios:
                if "node reboot" in scenario_name.lower():
                    bottlenecks["potential_bottlenecks"].append({
                        "type": "node_recovery",
                        "severity": "medium",
                        "description": f"Node reboot scenario failed: {scenario_name}",
                        "category": "compute"
                    })
                elif "ovn" in scenario_name.lower():
                    bottlenecks["potential_bottlenecks"].append({
                        "type": "ovn_stability",
                        "severity": "medium", 
                        "description": f"OVN-related scenario failed: {scenario_name}",
                        "category": "ovn"
                    })
            
            # Categorize bottlenecks
            for bottleneck in bottlenecks["identified_bottlenecks"] + bottlenecks["potential_bottlenecks"]:
                category = bottleneck.get("category", "unknown")
                if category in bottlenecks["bottleneck_categories"]:
                    bottlenecks["bottleneck_categories"][category].append(bottleneck)
            
            return bottlenecks
            
        except Exception as e:
            logger.error(f"Error identifying bottlenecks: {e}")
            return {"error": str(e)}
    
    async def _analyze_resource_utilization(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cluster resource utilization during test"""
        try:
            utilization = {
                "estimated_resource_usage": {},
                "efficiency_metrics": {},
                "resource_recommendations": []
            }
            
            # Estimate resource usage based on test configuration
            test_config = test_results.get("test_info", {}).get("config", {})
            eip_objects = test_config.get("eip_object_count", 10)
            pods_per_eip = test_config.get("pods_per_eip", 200)
            total_pods = eip_objects * pods_per_eip
            
            utilization["estimated_resource_usage"] = {
                "total_pods_created": total_pods,
                "estimated_cpu_cores": total_pods * 0.01,  # 10m CPU per pod
                "estimated_memory_mb": total_pods * 64,    # 64Mi memory per pod
                "network_interfaces": eip_objects * 2      # 2 IPs per EgressIP object
            }
            
            # Calculate efficiency metrics
            execution_time = test_results.get("execution_summary", {}).get("execution_time_seconds", 0)
            if execution_time > 0:
                utilization["efficiency_metrics"] = {
                    "pods_per_second": total_pods / execution_time,
                    "test_density": total_pods / (execution_time / 3600),  # pods per hour
                    "resource_efficiency": "high" if total_pods > 1000 else "medium"
                }
            
            return utilization
            
        except Exception as e:
            logger.error(f"Error analyzing resource utilization: {e}")
            return {"error": str(e)}
    
    async def _analyze_scaling_behavior(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze how the system behaves under different scales"""
        try:
            scaling = {
                "scale_characteristics": {},
                "scaling_limits": {},
                "scaling_recommendations": []
            }
            
            test_config = test_results.get("test_info", {}).get("config", {})
            total_pods = test_config.get("eip_object_count", 10) * test_config.get("pods_per_eip", 200)
            
            # Categorize scale level
            if total_pods < 500:
                scale_level = "small"
            elif total_pods < 1500:
                scale_level = "medium"
            else:
                scale_level = "large"
            
            scaling["scale_characteristics"] = {
                "scale_level": scale_level,
                "total_workload": total_pods,
                "scale_efficiency": self._calculate_scale_efficiency(test_results)
            }
            
            # Generate scaling recommendations
            if scale_level == "large" and test_results.get("execution_summary", {}).get("status") == "passed":
                scaling["scaling_recommendations"].append("System handles large scale well - consider testing higher limits")
            elif scale_level == "small":
                scaling["scaling_recommendations"].append("Consider testing with higher pod counts to validate scalability")
            
            return scaling
            
        except Exception as e:
            logger.error(f"Error analyzing scaling behavior: {e}")
            return {"error": str(e)}
    
    def _calculate_scale_efficiency(self, test_results: Dict[str, Any]) -> float:
        """Calculate efficiency score for current scale"""
        try:
            # Simple efficiency calculation based on success rate and execution time
            status = test_results.get("execution_summary", {}).get("status")
            execution_time = test_results.get("execution_summary", {}).get("execution_time_seconds", 0)
            
            if status == "passed":
                base_efficiency = 0.8
            else:
                base_efficiency = 0.4
            
            # Adjust based on execution time (assuming 6 hours is baseline)
            time_factor = min(1.0, 21600 / max(execution_time, 1))  # 6 hours = 21600 seconds
            
            return base_efficiency * time_factor
            
        except Exception as e:
            logger.error(f"Error calculating scale efficiency: {e}")
            return 0.5
    
    async def _generate_optimization_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on analysis"""
        try:
            recommendations = []
            
            # Analyze test status and generate recommendations
            status = test_results.get("execution_summary", {}).get("status")
            execution_time = test_results.get("execution_summary", {}).get("execution_time_seconds", 0)
            
            if status != "passed":
                recommendations.append("Test failures detected - review cluster resources and network configuration")
                recommendations.append("Check OVN-Kubernetes pod logs for errors during test execution")
                recommendations.append("Verify cluster has sufficient CPU and memory for large-scale testing")
            
            if execution_time > 21600:  # 6 hours
                recommendations.append("Test execution time is high - consider optimizing cluster performance")
                recommendations.append("Review node resource allocation and consider adding more worker nodes")
                recommendations.append("Check for network bottlenecks that might slow pod creation")
            
            # Configuration-based recommendations
            test_config = test_results.get("test_info", {}).get("config", {})
            iterations = test_config.get("iterations", 20)
            
            if iterations < 10:
                recommendations.append("Consider increasing iteration count for more comprehensive testing")
            
            # Performance metrics recommendations
            performance_metrics = test_results.get("test_results", {}).get("performance_metrics", {})
            if not performance_metrics.get("snat_rules_validated", False):
                recommendations.append("SNAT rules validation failed - investigate OVN rule configuration")
            
            if not performance_metrics.get("lrp_rules_validated", False):
                recommendations.append("LRP rules validation failed - check logical router policies")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating optimization recommendations: {e}")
            return ["Error generating recommendations - check logs for details"]
    
    async def _generate_performance_insights(self, analysis: Dict[str, Any]) -> List[PerformanceInsight]:
        """Generate performance insights based on comprehensive analysis"""
        try:
            insights = []
            
            # Test summary insights
            test_summary = analysis.get("test_summary", {})
            performance_score = test_summary.get("performance_score", 0)
            
            if performance_score >= 80:
                insights.append(PerformanceInsight(
                    category="overall",
                    severity="info",
                    title="Excellent Performance",
                    description=f"Test achieved high performance score of {performance_score:.1f}/100",
                    recommendations=["Maintain current configuration", "Consider testing higher scales"]
                ))
            elif performance_score >= 60:
                insights.append(PerformanceInsight(
                    category="overall",
                    severity="warning",
                    title="Moderate Performance",
                    description=f"Test achieved moderate performance score of {performance_score:.1f}/100",
                    recommendations=["Review resource allocation", "Investigate performance bottlenecks"]
                ))
            else:
                insights.append(PerformanceInsight(
                    category="overall",
                    severity="critical",
                    title="Poor Performance",
                    description=f"Test achieved low performance score of {performance_score:.1f}/100",
                    recommendations=["Immediate performance optimization needed", "Check cluster health"]
                ))
            
            # Bottleneck insights
            bottlenecks = analysis.get("bottleneck_analysis", {})
            identified_bottlenecks = bottlenecks.get("identified_bottlenecks", [])
            
            if identified_bottlenecks:
                for bottleneck in identified_bottlenecks:
                    insights.append(PerformanceInsight(
                        category="bottleneck",
                        severity=bottleneck.get("severity", "warning"),
                        title=f"Performance Bottleneck: {bottleneck.get('type', 'Unknown')}",
                        description=bottleneck.get("description", ""),
                        recommendations=[f"Address {bottleneck.get('category', 'system')} performance issues"]
                    ))
            
            # Resource utilization insights
            utilization = analysis.get("resource_utilization", {})
            efficiency = utilization.get("efficiency_metrics", {}).get("resource_efficiency", "unknown")
            
            if efficiency == "high":
                insights.append(PerformanceInsight(
                    category="resources",
                    severity="info",
                    title="Efficient Resource Usage",
                    description="Test demonstrated efficient use of cluster resources",
                    recommendations=["Resource allocation is optimal for current workload"]
                ))
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating performance insights: {e}")
            return []


async def main():
    """Main function for standalone testing"""
    analyzer = EgressIPPerformanceDeepDive()
    
    # Sample test results for demonstration
    sample_results = {
        "execution_summary": {
            "status": "passed",
            "execution_time_seconds": 18000  # 5 hours
        },
        "test_results": {
            "scenarios": {
                "scenario1": {"passed": True, "iterations_completed": 20},
                "scenario2": {"passed": True, "iterations_completed": 20},
                "scenario3": {"passed": False, "iterations_completed": 15},
                "scenario4": {"passed": True, "iterations_completed": 20}
            },
            "performance_metrics": {
                "snat_rules_validated": True,
                "lrp_rules_validated": True
            }
        },
        "test_info": {
            "config": {
                "eip_object_count": 10,
                "pods_per_eip": 200,
                "iterations": 20
            }
        }
    }
    
    analysis = await analyzer.analyze_test_performance(sample_results)
    print(json.dumps(analysis, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())