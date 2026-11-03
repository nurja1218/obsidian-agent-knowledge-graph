---
title: 중복 결제 장애 기록
created: 2026-03-15
status: completed
type: incident
domain: payments
moc: "[[payments]]"
depends-on: ["[[2026-03-02-checkout-v2-spec]]", "[[2026-02-01-webhook-retry-runbook]]"]
implements: fix/duplicate-charge
---

# 중복 결제 장애

웹훅 재전송이 멱등 키 검사 전에 처리돼 2건 중복 결제. 검사 순서를 바꿔 수정.
