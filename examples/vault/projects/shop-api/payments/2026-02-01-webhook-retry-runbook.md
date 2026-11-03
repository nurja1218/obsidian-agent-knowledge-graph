---
title: PG 웹훅 재시도 런북
created: 2026-02-01
status: in-progress
domain: payments
moc: "[[payments]]"
depends-on: ["[[2026-01-20-idempotency-key-decision]]"]
---

# 웹훅 재시도 런북

웹훅은 같은 이벤트가 여러 번 올 수 있다 — 멱등 키 결정을 전제로 한다.
