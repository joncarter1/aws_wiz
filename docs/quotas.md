# AWS EC2 GPU & Accelerator Service Quotas

This document lists the primary quota buckets for GPU and specialized ML instances. Use `awiz quota-check` to see your live limits.

| Quota Type | Exact Quota Name                              | Code       | Included Instance Families |
|:-----------|:----------------------------------------------|:-----------|:---------------------------|
| On-Demand  | **Running On-Demand G and VT instances**      | L-DB2E81BA | G3, G4, G5, G6, G7, VT1    |
| On-Demand  | **Running On-Demand P instances**             | L-417A185B | P2, P3, P4, P5, P5en       |
|            |                                               |            |                            |
| Spot       | **All G and VT Spot Instance Requests**       | L-3819A6DF | G3, G4, G5, G6, G7, VT1    |
| Spot       | **All P4, P3 and P2 Spot Instance Requests**  | L-7212CCBC | P2, P3, P4                 |
| Spot       | **All P5 Spot Instance Requests**             | L-C4BD4855 | P5, P5e, P5en              |


---
*Note: P6 (Blackwell) and some high-end P5 allocations are managed via **EC2 Capacity Blocks**, which are separate from these standard quotas.*
