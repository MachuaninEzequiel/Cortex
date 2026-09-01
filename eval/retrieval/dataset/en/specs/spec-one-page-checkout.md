---
title: Spec: One-page checkout flow
tags: [checkout]
---

## Goal
Reduce cart abandonment by implementing a single-page checkout.
## Verification hooks
tests/checkout/test_one_page.py must pass.
## Scope
The checkout validates the card, computes shipping and confirms the order without page reloads.
