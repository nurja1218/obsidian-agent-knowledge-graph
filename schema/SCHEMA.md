# 스키마

## 기억 노트 (`memory/<slug>.md`)

```yaml
---
name: <slug>                         # 파일 이름과 같다 — [[slug]] 로 링크된다
description: <한 줄 요약>             # 허브·색인에 그대로 쓰이는 문장
metadata:
  type: user | feedback | project | reference
  modified: <ISO 시각>                # 마지막 수정
  originSessionId: <세션 id>          # 이 사실을 처음 알게 된 대화
---

<사실 한 개. feedback · project 는 이어서>
**Why:** <이유>
**How to apply:** <언제 어떻게 적용하나>
관련: [[다른-기억]]
```

- 허브 `MEMORY.md` 에는 `- [제목](파일.md) — 한 줄` 만. 내용은 사실 노트에.
- 허브가 커지면 주제별 색인(`index-<주제>.md`)으로 옮기고 허브에는 색인 링크만 남긴다.
- 아직 없는 노트로의 `[[링크]]` 는 허용 — "써야 할 기억" 표시.

## 작업 노트 (`projects/<레포>/<도메인>/...md`)

```yaml
---
title: <제목>
created: <YYYY-MM-DD>
status: draft | active | in-progress | done | implemented | archived | superseded
type: spec | decision | progress | incident | reference   # 선택
domain: <도메인 slug>              # 필수 — 에이전트의 1차 질의 키
moc: "[[<domain>]]"                # 도메인 허브가 있으면 필수
depends-on: ["[[..]]", "[[..]]"]   # 이 노트를 읽을 때 같이 읽을 노트
superseded-by: "[[..]]"            # 이 노트를 대체한 노트 (대체됐을 때만)
implements: <branch> @ <commit>    # 코드 산출물이 있을 때 (값, 링크 아님)
---
```

- 블록 목록도 된다: `depends-on:` 다음 줄부터 `  - "[[..]]"`.
- 세션 인계 노트는 날짜로 시작하는 이름으로 쓰고, 새 인계를 쓸 때 직전 인계에 `superseded-by` 를 건다.

## 도메인 허브 (`_meta/moc/<domain>.md`)

````markdown
---
title: <Domain> (도메인 MOC)
type: moc
domain: <domain>
---

```base
filters:
  and:
    - domain == "<domain>"
views:
  - type: table
    order: [file.name, status, implements]
```
````

파일 이름 = 도메인 slug 라 어디서든 `[[<domain>]]` 로 링크된다. Bases 표가 안 보여도 각 노트의 `moc` 링크로 백링크 패널에 전부 뜬다.

## 기존 vault 에 도입할 때

1. **기계적** — `domain` · `moc` · `created` · `status` 를 채우고 허브를 만든다. 스크립트로 일괄.
2. **의미적** — `depends-on` · `superseded-by` · `implements` 는 도메인 하나씩 노트를 읽고 직접 적는다. 1번만 하면 "구조는 있고 연결은 없는" 반쪽 그래프가 된다.
