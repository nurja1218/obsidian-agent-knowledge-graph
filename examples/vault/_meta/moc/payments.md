---
title: Payments (도메인 MOC)
type: moc
domain: payments
---

# Payments — 도메인 허브

각 노트의 `moc: "[[payments]]"` 가 이 노트로 모인다. Obsidian 에서는 아래 Bases 블록이 `domain == "payments"` 노트를 표로 보여 준다.

```base
filters:
  and:
    - domain == "payments"
views:
  - type: table
    name: payments 노트
    order:
      - file.name
      - status
      - implements
```
