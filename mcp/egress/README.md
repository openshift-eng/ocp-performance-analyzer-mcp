# EgressIP Performance Analyzer MCP Server

A comprehensive AI-powered performance analysis and testing platform for OpenShift EgressIP functionality, following the established OCP Performance Analyzer MCP repository structure.

## Overview

The EgressIP Performance Analyzer provides advanced testing, monitoring, and analysis capabilities for OpenShift EgressIP implementations. It integrates large-scale performance testing (like CORENET-6498) with continuous monitoring and AI-powered bottleneck detection.

## Repository Structure

Following the established patterns in the OCP Performance Analyzer MCP repository:

```
├── analysis/egress/                          # Performance analysis modules
│   └── egress_analyzer_performance_deepdrive.py
├── config/                                   # Configuration files  
│   └── config-egress.yml                     # EgressIP analyzer configuration
├── elt/egress/                              # Extract-Load-Transform processing
│   └── egress_analyzer_elt_processor.py
├── mcp/egress/                              # MCP server implementation
│   └── egress_analyzer_mcp_server.py
├── tools/egressip/                          # Data collection tools
│   ├── corenet_6498_runner.py               # CORNET-6498 test integration
│   ├── ovn_rule_analyzer.py                 # OVN rule analysis
│   └── metrics_collector.py                 # Metrics collection
└── storage/                                 # Data storage (auto-created)
    └── egress_*.db                          # SQLite databases
```

## Features

### 🚀 **Large-Scale Performance Testing**
- **CORENET-6498 Integration**: Execute large-scale EgressIP stress tests with 2000+ pods
- **Multi-Scenario Testing**: Node reboots, OVN pod restarts, scaling operations under load
- **IPv4/IPv6 Support**: Comprehensive dual-stack testing capabilities
- **Automated Validation**: SNAT/LRP rule consistency verification across test scenarios

### 🔍 **Advanced OVN Analysis**
- **Real-time Rule Validation**: Live SNAT and LRP rule consistency checking
- **Cross-node Comparison**: Multi-node rule consistency validation
- **Rule Change Monitoring**: Continuous monitoring for rule instability detection
- **Performance Correlation**: Direct correlation between OVN rules and performance metrics

### 📊 **ELT Data Processing**
- **Extract**: Raw data extraction from tests and metrics
- **Transform**: Structured data transformation for analysis
- **Load**: Persistent storage with SQLite backend
- **Historical Analysis**: Long-term performance pattern identification

### 🤖 **AI-Powered Analysis**
- **Natural Language Interface**: Query EgressIP performance using natural language
- **Automated Recommendations**: AI-generated optimization suggestions
- **Deep Dive Analysis**: Comprehensive performance pattern analysis
- **Predictive Insights**: Trend-based performance predictions

## Configuration

The EgressIP analyzer uses the centralized configuration approach:

**Location**: `config/config-egress.yml`

Key configuration sections:
```yaml
# Test Configuration
test_config:
  cornet_6498:
    default_eip_objects: 10
    default_pods_per_eip: 200
    default_iterations: 20

# Performance Thresholds
performance_thresholds:
  rule_validation:
    max_snat_rules_per_node: 10000
    rule_consistency_min_score: 0.8

# Metrics Collection
metrics:
  collection_schedule:
    egressip_metrics_interval_minutes: 15
    ovn_rules_interval_minutes: 30
```

## MCP Tools

The server provides 5 specialized MCP tools:

1. **`run_cornet_6498_test`**: Execute CORNET-6498 large-scale EgressIP stress test
2. **`validate_snat_lrp_rules`**: Validate SNAT/LRP rules consistency on specific nodes  
3. **`analyze_egressip_performance`**: Analyze EgressIP performance and identify bottlenecks
4. **`get_egressip_status`**: Get comprehensive EgressIP status across the cluster
5. **`monitor_ovn_rules`**: Monitor OVN rule changes over time for stability analysis

## Quick Start

### Prerequisites
- OpenShift cluster with OVN-Kubernetes networking
- Python 3.8+
- Go 1.19+ (for test execution)
- `oc` CLI tool configured

### Installation

1. **Start the MCP server**:
   ```bash
   cd mcp/egress
   python egress_analyzer_mcp_server.py
   ```

2. **Configuration** (optional):
   - Edit `config/config-egress.yml` for custom settings
   - Adjust test parameters and thresholds as needed

### Usage Examples

#### Natural Language Queries (via AI agents)
```bash
"Run a CORNET-6498 test with 5 EgressIP objects and 100 pods each"
"Check if SNAT rules are consistent on worker-0"  
"Show me EgressIP performance trends from the last week"
"What's the current status of all EgressIP objects?"
```

#### Programmatic Usage
```python
# Execute large-scale EgressIP test
result = await run_cornet_6498_test(
    eip_object_count=10,
    pods_per_eip=200,
    iterations=20,
    ip_stack="ipv4"
)

# Validate OVN rules
validation = await validate_snat_lrp_rules("worker-0")

# Analyze performance
analysis = await analyze_egressip_performance("test-namespace")
```

## Integration with Existing Go Tests

The implementation provides seamless integration with existing Go test infrastructure:

- **Preserves Existing Logic**: Original `corenet_6498_test.go` runs unchanged
- **Python Bridge**: Wrapper for Go test execution and result parsing in `tools/egressip/corenet_6498_runner.py`
- **Enhanced Analysis**: Advanced metrics collection via `analysis/egress/egress_analyzer_performance_deepdrive.py`
- **Data Processing**: ELT pipeline in `elt/egress/egress_analyzer_elt_processor.py`

## Data Flow

```
Go Tests → tools/egressip → elt/egress → analysis/egress → mcp/egress → AI Agents
    ↓           ↓              ↓             ↓              ↓
Raw Results  Extract    Transform     Analyze      MCP Tools    Natural Language
```

## Component Details

### **Analysis Component** (`analysis/egress/`)
- Deep dive performance analysis
- Bottleneck identification
- Performance pattern recognition
- Optimization recommendations

### **ELT Component** (`elt/egress/`)
- Data extraction from multiple sources
- Structured transformation for analysis
- Persistent loading into SQLite storage
- Historical data management

### **Tools Component** (`tools/egressip/`)
- CORNET-6498 test runner and integration
- OVN rule analyzer with consistency checking
- Comprehensive metrics collection
- Cluster resource monitoring

### **MCP Server** (`mcp/egress/`)
- FastMCP-based server implementation
- 5 specialized tools for EgressIP analysis
- Configuration-driven behavior
- AI agent integration

## Testing and Validation

- **Unit Tests**: Core functionality validation
- **Integration Tests**: End-to-end test execution
- **MCP Protocol Tests**: Tool interface validation
- **Performance Tests**: Large-scale scenario validation

## Dependencies

- Python 3.8+ with FastMCP framework
- OpenShift/Kubernetes cluster with OVN-Kubernetes
- Go 1.19+ and Ginkgo (for test execution)
- SQLite for data storage

## Contributing

Follow the established repository patterns:
- Use the modular structure (`analysis/`, `elt/`, `tools/`, `mcp/`)
- Place configurations in the central `config/` directory
- Follow naming conventions: `*_analyzer_*` for components
- Maintain separation of concerns between components

---

**Tested on**: OpenShift 4.16.8 with OVN-Kubernetes  
**Compatible with**: AWS, GCP, Azure, OpenStack, vSphere, Bare Metal platforms  
**AI Agents**: Claude, and other MCP-compatible agents