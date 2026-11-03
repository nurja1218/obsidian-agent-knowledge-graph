---
title: 결제 요청 멱등 키 도입 결정
created: 2026-01-20
status: accepted
type: decision
domain: payments
moc: "[[payments]]"
---

# 결정: 결제 요청에 멱등 키

클라이언트가 요청마다 키를 보내고, 서버는 같은 키의 두 번째 요청에 첫 결과를 그대로 돌려준다.
기각: 서버 측 시간 창 중복 검사 — 정상 재구매까지 막는다.
