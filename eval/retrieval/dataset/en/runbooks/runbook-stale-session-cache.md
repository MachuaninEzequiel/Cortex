---
title: Runbook: Stale session cache
tags: [ops]
---

## Symptoms
Users randomly logged out or seeing other people's data.
## Diagnosis
Check Redis evictions and pub/sub desynchronization.
## Mitigation
Targeted flush of the session namespace and gradual pod restart.
