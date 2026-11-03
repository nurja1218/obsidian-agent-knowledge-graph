---
title: 결제 API v2 명세
created: 2026-03-02
status: completed
domain: payments
moc: "[[payments]]"
depends-on:
  - "[[2026-01-20-idempotency-key-decision]]"
  - "[[order-state-machine]]"
implements: feature/checkout-v2 @ 3f2a91c
---

# 결제 API v2 명세

v1 을 대체한다. 멱등 키 필수, 주문 상태 전이는 [[order-state-machine]] 을 따른다.
