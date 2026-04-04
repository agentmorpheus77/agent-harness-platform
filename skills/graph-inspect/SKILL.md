---
name: graph-inspect
description: Use when the user wants to inspect, diagnose, or audit Neo4j knowledge graph health — statistics, ontology compliance, orphans, facts, embeddings, duplicates, or cross-instance comparison
version: 0.1.0
---

# Graph Inspect

Diagnose graph health across CDB-TQS Neo4j knowledge graph instances powered by Graphiti.

## Tools

### inspect
Run health inspections on Neo4j knowledge graphs. Supports 7 modes plus an `all` mode that runs everything.

**Call:**
```bash
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/graph_inspect.py --mode <mode> [--knowledge-area <ka>] [--api-url <url>]
```

**Parameters:**
| Parameter | Required | Description |
|-----------|----------|-------------|
| --mode | Yes | overview, ontology-check, orphans, facts, embeddings, duplicates, instance-compare, or all |
| --knowledge-area | No | Filter by knowledge area (e.g., ecpd, general) |
| --api-url | No | Backend API URL (default: $GRAPH_API_URL or http://localhost:8000) |

**Modes:**
| Mode | What it checks | Data source |
|------|---------------|-------------|
| overview | Node/edge counts, instance health, driver pool | Backend API |
| ontology-check | Labels vs ontology definitions, edge type compliance, property completeness | Neo4j Cypher |
| orphans | Entities with no episode references, isolated nodes | Neo4j Cypher |
| facts | Fact status distribution, review backlog, temporal analysis | Neo4j Cypher |
| embeddings | name_embedding coverage per knowledge area | Neo4j Cypher |
| duplicates | Case-insensitive name duplicates, identical summaries | Neo4j Cypher |
| instance-compare | Cross-instance stats and health comparison | Backend API |
| all | Runs all modes above | Both |

**Environment variables:**
| Variable | Default | Description |
|----------|---------|-------------|
| GRAPH_API_URL | http://localhost:8000 | Backend API base URL |
| NEO4J_URI | bolt://localhost:7687 | Neo4j Bolt URI |
| NEO4J_USER | neo4j | Neo4j username |
| NEO4J_PASSWORD | (required for Cypher modes) | Neo4j password |
| AUTH_TOKEN | (optional) | Bearer token for authenticated API endpoints |

**Examples:**
```bash
# Full overview via API
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/graph_inspect.py --mode overview

# Find orphaned entities in the ecpd knowledge area
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/graph_inspect.py --mode orphans --knowledge-area ecpd

# Check embedding coverage
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/graph_inspect.py --mode embeddings

# Run all inspections
~/.cdb-skills/venv/bin/python {SKILL_DIR}/tools/graph_inspect.py --mode all
```

## When to use
- Diagnosing knowledge graph health or data quality issues
- Before or after bulk data ingestion to verify integrity
- Checking ontology compliance after schema changes
- Finding orphaned or duplicate entities for cleanup
- Verifying embedding coverage for semantic search quality
- Comparing graph instances in multi-instance deployments

## When NOT to use
- For querying graph content (use the graph search API directly)
- For modifying graph data (use the admin API or Graphiti services)
- For application-level debugging (check application logs instead)
