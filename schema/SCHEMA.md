# 노트 스키마

## 일반 노트

```yaml
---
title: <제목>
created: <YYYY-MM-DD>
status: proposed | in-progress | completed | superseded | accepted
type: spec | decision | progress | incident | reference   # 선택
domain: <도메인 slug>              # 필수 — 에이전트의 1차 질의 키
moc: "[[<domain>]]"                # 도메인 허브가 있으면 필수
depends-on: ["[[..]]", "[[..]]"]   # 이 노트가 기반으로 삼는 노트
superseded-by: "[[..]]"            # 이 노트를 대체한 노트 (대체됐을 때만)
implements: <branch> @ <commit>    # 코드 산출물이 있을 때 (값, 링크 아님)
---
```

- 블록 목록도 된다: `depends-on:` 다음 줄부터 `  - "[[..]]"`.
- `related` 는 쓰지 않는다. 관계 이유를 한 줄로 못 적으면 엣지가 아니다.

## 도메인 허브 (MOC)

위치 `_meta/moc/<domain>.md` — 파일 이름 = 도메인 slug 라 어디서든 `[[<domain>]]` 로 링크된다.

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

Bases 표가 안 보이는 Obsidian 버전이어도, 각 노트의 `moc` 링크 때문에 백링크 패널에 전부 뜬다.

## 기존 vault 에 도입할 때 (두 층)

1. **기계적** — `domain`·`moc`·`created`·`status` 필드를 채우고 허브를 만든다. 스크립트로 일괄 처리 가능.
2. **의미적** — `depends-on`·`superseded-by`·`implements` 는 도메인 하나씩 노트를 읽고 직접 적는다. 1번만 하고 멈추면 "구조는 있고 연결은 없는" 반쪽 그래프가 된다.
