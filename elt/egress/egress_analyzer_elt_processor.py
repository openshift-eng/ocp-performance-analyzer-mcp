#!/usr/bin/env python3
"""
EgressIP Analyzer ELT (Extract, Load, Transform) Processor

This module handles data extraction from test results and metrics,
transformation for analysis, and loading into storage systems.

Author: Performance Scale Team
License: Apache-2.0
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EgressIPAnalyzerELT:
    """ELT processor for EgressIP performance data"""
    
    def __init__(self, storage_path: str = "./storage/egress_elt.db"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_storage()
    
    def init_storage(self):
        """Initialize storage schema for ELT processing"""
        try:
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                
                # Raw data extraction table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS elt_extractions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        extraction_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        source_type TEXT NOT NULL,
                        data_json TEXT NOT NULL,
                        metadata_json TEXT
                    )
                """)
                
                # Transformed performance metrics
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS elt_transformed_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        extraction_id TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        metric_unit TEXT,
                        timestamp TEXT NOT NULL,
                        labels_json TEXT,
                        FOREIGN KEY (extraction_id) REFERENCES elt_extractions(extraction_id)
                    )
                """)
                
                # Aggregated insights
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS elt_insights (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        extraction_id TEXT NOT NULL,
                        insight_type TEXT NOT NULL,
                        insight_title TEXT NOT NULL,
                        insight_description TEXT,
                        severity TEXT,
                        recommendations_json TEXT,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (extraction_id) REFERENCES elt_extractions(extraction_id)
                    )
                """)
                
                # Create indices
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_extractions_timestamp ON elt_extractions(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON elt_transformed_metrics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_insights_type ON elt_insights(insight_type)")
                
                conn.commit()
                logger.info("ELT storage initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing ELT storage: {e}")
            raise
    
    async def extract_test_results(self, test_results: Dict[str, Any], source_type: str = "cornet_6498") -> str:
        """
        Extract test results data for ELT processing
        
        Args:
            test_results: Raw test results data
            source_type: Type of data source
            
        Returns:
            Extraction ID for tracking
        """
        try:
            extraction_id = f"{source_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            timestamp = datetime.utcnow().isoformat()
            
            metadata = {
                "source_type": source_type,
                "extraction_timestamp": timestamp,
                "data_size": len(json.dumps(test_results)),
                "test_config": test_results.get("test_info", {}).get("config", {}),
                "test_status": test_results.get("execution_summary", {}).get("status", "unknown")
            }
            
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO elt_extractions 
                    (extraction_id, timestamp, source_type, data_json, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    extraction_id,
                    timestamp,
                    source_type,
                    json.dumps(test_results),
                    json.dumps(metadata)
                ))
                conn.commit()
            
            logger.info(f"Extracted test results with ID: {extraction_id}")
            return extraction_id
            
        except Exception as e:
            logger.error(f"Error extracting test results: {e}")
            raise
    
    async def extract_metrics_data(self, metrics_data: Dict[str, Any], source_type: str = "metrics_collector") -> str:
        """
        Extract metrics data for ELT processing
        
        Args:
            metrics_data: Raw metrics data
            source_type: Type of metrics source
            
        Returns:
            Extraction ID for tracking
        """
        try:
            extraction_id = f"{source_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            timestamp = datetime.utcnow().isoformat()
            
            metadata = {
                "source_type": source_type,
                "extraction_timestamp": timestamp,
                "metrics_count": len(metrics_data.get("metrics", [])),
                "collection_timestamp": metrics_data.get("timestamp", timestamp)
            }
            
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO elt_extractions 
                    (extraction_id, timestamp, source_type, data_json, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    extraction_id,
                    timestamp,
                    source_type,
                    json.dumps(metrics_data),
                    json.dumps(metadata)
                ))
                conn.commit()
            
            logger.info(f"Extracted metrics data with ID: {extraction_id}")
            return extraction_id
            
        except Exception as e:
            logger.error(f"Error extracting metrics data: {e}")
            raise
    
    async def transform_performance_data(self, extraction_id: str) -> Dict[str, Any]:
        """
        Transform extracted data into structured performance metrics
        
        Args:
            extraction_id: ID of the extraction to transform
            
        Returns:
            Transformation results summary
        """
        try:
            logger.info(f"Starting transformation for extraction: {extraction_id}")
            
            # Retrieve extracted data
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT data_json, source_type, metadata_json 
                    FROM elt_extractions 
                    WHERE extraction_id = ?
                """, (extraction_id,))
                
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"No extraction found with ID: {extraction_id}")
                
                data_json, source_type, metadata_json = row
                raw_data = json.loads(data_json)
                metadata = json.loads(metadata_json)
            
            # Transform based on source type
            if source_type == "cornet_6498":
                transformation_result = await self._transform_test_results(extraction_id, raw_data)
            elif source_type == "metrics_collector":
                transformation_result = await self._transform_metrics_data(extraction_id, raw_data)
            else:
                transformation_result = await self._transform_generic_data(extraction_id, raw_data)
            
            logger.info(f"Transformation completed for {extraction_id}")
            return transformation_result
            
        except Exception as e:
            logger.error(f"Error transforming data for {extraction_id}: {e}")
            raise
    
    async def _transform_test_results(self, extraction_id: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CORNET-6498 test results into metrics"""
        try:
            transformed_metrics = []
            timestamp = datetime.utcnow().isoformat()
            
            # Extract execution metrics
            execution_summary = test_data.get("execution_summary", {})
            
            metrics_to_extract = [
                ("execution_time_seconds", execution_summary.get("execution_time_seconds", 0), "seconds"),
                ("test_status_numeric", 1 if execution_summary.get("status") == "passed" else 0, "boolean"),
                ("exit_code", execution_summary.get("exit_code", -1), "code")
            ]
            
            # Test results metrics
            test_results = test_data.get("test_results", {})
            scenarios = test_results.get("scenarios", {})
            
            completed_scenarios = sum(1 for s in scenarios.values() if s.get("passed", False))
            total_scenarios = len(scenarios)
            
            metrics_to_extract.extend([
                ("scenarios_completed", completed_scenarios, "count"),
                ("scenarios_total", total_scenarios, "count"),
                ("success_rate", completed_scenarios / total_scenarios if total_scenarios > 0 else 0, "percentage")
            ])
            
            # Performance metrics
            performance_metrics = test_results.get("performance_metrics", {})
            
            metrics_to_extract.extend([
                ("pods_created", performance_metrics.get("pod_count_achieved", 0), "count"),
                ("egressip_objects", performance_metrics.get("egressip_objects_created", 0), "count"),
                ("snat_rules_validated", 1 if performance_metrics.get("snat_rules_validated", False) else 0, "boolean"),
                ("lrp_rules_validated", 1 if performance_metrics.get("lrp_rules_validated", False) else 0, "boolean")
            ])
            
            # Store transformed metrics
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                
                for metric_name, metric_value, metric_unit in metrics_to_extract:
                    cursor.execute("""
                        INSERT INTO elt_transformed_metrics
                        (extraction_id, metric_name, metric_value, metric_unit, timestamp, labels_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        extraction_id,
                        metric_name,
                        float(metric_value),
                        metric_unit,
                        timestamp,
                        json.dumps({"source": "cornet_6498"})
                    ))
                
                conn.commit()
            
            return {
                "transformation_type": "test_results",
                "metrics_transformed": len(metrics_to_extract),
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error transforming test results: {e}")
            raise
    
    async def _transform_metrics_data(self, extraction_id: str, metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform metrics collector data"""
        try:
            transformed_metrics = []
            timestamp = datetime.utcnow().isoformat()
            
            metrics = metrics_data.get("metrics", [])
            
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                
                for metric in metrics:
                    if isinstance(metric, dict):
                        # Extract numeric metrics from the metric data
                        metric_name = metric.get("name", "unknown_metric")
                        
                        # Extract various numeric fields
                        numeric_fields = ["pod_count", "assigned_nodes", "assigned_ips"]
                        
                        for field in numeric_fields:
                            if field in metric:
                                value = metric[field]
                                if isinstance(value, (int, float)):
                                    cursor.execute("""
                                        INSERT INTO elt_transformed_metrics
                                        (extraction_id, metric_name, metric_value, metric_unit, timestamp, labels_json)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (
                                        extraction_id,
                                        f"{metric_name}_{field}",
                                        float(value),
                                        "count",
                                        timestamp,
                                        json.dumps({"source": "metrics_collector", "metric_object": metric_name})
                                    ))
                
                conn.commit()
            
            return {
                "transformation_type": "metrics_data",
                "metrics_processed": len(metrics),
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error transforming metrics data: {e}")
            raise
    
    async def _transform_generic_data(self, extraction_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform generic data into metrics"""
        try:
            # Basic transformation for unknown data types
            timestamp = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                
                # Store basic metrics about the data
                cursor.execute("""
                    INSERT INTO elt_transformed_metrics
                    (extraction_id, metric_name, metric_value, metric_unit, timestamp, labels_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    extraction_id,
                    "data_size_bytes",
                    float(len(json.dumps(raw_data))),
                    "bytes",
                    timestamp,
                    json.dumps({"source": "generic"})
                ))
                
                conn.commit()
            
            return {
                "transformation_type": "generic",
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error transforming generic data: {e}")
            raise
    
    async def load_insights(self, extraction_id: str, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load processed insights into storage
        
        Args:
            extraction_id: ID of the source extraction
            insights: List of insight dictionaries
            
        Returns:
            Load operation summary
        """
        try:
            timestamp = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                
                for insight in insights:
                    cursor.execute("""
                        INSERT INTO elt_insights
                        (extraction_id, insight_type, insight_title, insight_description, 
                         severity, recommendations_json, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        extraction_id,
                        insight.get("category", "general"),
                        insight.get("title", ""),
                        insight.get("description", ""),
                        insight.get("severity", "info"),
                        json.dumps(insight.get("recommendations", [])),
                        timestamp
                    ))
                
                conn.commit()
            
            logger.info(f"Loaded {len(insights)} insights for extraction {extraction_id}")
            return {
                "insights_loaded": len(insights),
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error loading insights: {e}")
            raise
    
    async def get_transformation_summary(self, days_back: int = 7) -> Dict[str, Any]:
        """Get summary of ELT transformations over time"""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
            
            with sqlite3.connect(self.storage_path) as conn:
                cursor = conn.cursor()
                
                # Get extraction summary
                cursor.execute("""
                    SELECT source_type, COUNT(*) as count
                    FROM elt_extractions
                    WHERE timestamp > ?
                    GROUP BY source_type
                """, (cutoff_date,))
                
                extractions = dict(cursor.fetchall())
                
                # Get metrics summary
                cursor.execute("""
                    SELECT COUNT(*) as total_metrics
                    FROM elt_transformed_metrics
                    WHERE timestamp > ?
                """, (cutoff_date,))
                
                total_metrics = cursor.fetchone()[0]
                
                # Get insights summary
                cursor.execute("""
                    SELECT insight_type, COUNT(*) as count
                    FROM elt_insights
                    WHERE timestamp > ?
                    GROUP BY insight_type
                """, (cutoff_date,))
                
                insights = dict(cursor.fetchall())
            
            return {
                "period_days": days_back,
                "extractions_by_source": extractions,
                "total_metrics_transformed": total_metrics,
                "insights_by_type": insights,
                "summary_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting transformation summary: {e}")
            return {"error": str(e)}


async def main():
    """Main function for standalone testing"""
    elt = EgressIPAnalyzerELT()
    
    # Sample test data
    sample_test_results = {
        "execution_summary": {
            "status": "passed",
            "execution_time_seconds": 3600,
            "exit_code": 0
        },
        "test_results": {
            "scenarios": {
                "scenario1": {"passed": True},
                "scenario2": {"passed": True}
            },
            "performance_metrics": {
                "pod_count_achieved": 1000,
                "egressip_objects_created": 5,
                "snat_rules_validated": True,
                "lrp_rules_validated": True
            }
        }
    }
    
    # Test ELT pipeline
    extraction_id = await elt.extract_test_results(sample_test_results)
    transformation_result = await elt.transform_performance_data(extraction_id)
    
    print(f"ELT Test Results:")
    print(f"Extraction ID: {extraction_id}")
    print(f"Transformation: {json.dumps(transformation_result, indent=2)}")
    
    summary = await elt.get_transformation_summary()
    print(f"Summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())