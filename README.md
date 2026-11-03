# obsidian-agent-knowledge-graph

Obsidian vault 의 마크다운 노트를 **AI 에이전트가 따라가고 질의할 수 있는 typed-edge 지식그래프**로 쓰는 규약과 도구입니다.
2026년 5월부터 매일 쓰는 개인 vault(노트 약 1,400개)에서 회사·개인 내용을 빼고 구조·규칙·도구만 남겼습니다.

![예시 그래프](docs/knowledge-graph.svg)

## 왜

노트에 frontmatter 는 거의 다 있었지만 연결이 없었습니다 — 도입 전(2026-07-01) 실측 282개 중 **74%가 아무 노트와도 이어지지 않은 고아**.
Obsidian 그래프는 흩어진 점이었고, 무엇보다 **에이전트는 그래프 그림을 보지 못하고 frontmatter 를 읽습니다**.
그래서 목표를 "보기 좋은 그래프"가 아니라 **에이전트가 순회할 수 있는 타입 있는 엣지 + 고정된 진입점**으로 잡았습니다.

## 모델

| 그래프 | 노트에서 | 쓰임 |
|---|---|---|
| 노드 | 마크다운 노트 1개 | |
| 속성 | frontmatter — `domain` · `status` · `type` · `created` | `domain` = 에이전트의 1차 질의 키 |
| 허브 | 도메인 MOC `_meta/moc/<domain>.md` + Bases 블록 | 파일을 옮기지 않고 `domain == "<x>"` 노트를 한 표로 (Obsidian 화면) |
| 엣지 `moc` | `moc: "[[payments]]"` | 노트 → 도메인 허브 |
| 엣지 `depends-on` | `depends-on: ["[[결정]]", ...]` | A 를 읽을 때 B 도 같이 읽는다 |
| 엣지 `superseded-by` | `superseded-by: "[[v2]]"` | **시간 축** — 옛 노트에서 현재 기준 노트로 |
| 엣지 `implements` | `implements: feature/checkout-v2 @ 3f2a91c` | 노트 ↔ 브랜치·커밋 (값만, 링크 아님) |

**규칙** (스키마보다 중요)
- 엣지는 위 4종만. 이유를 한 줄로 못 적는 `related` 는 쓰지 않는다.
- **없는 관계를 지어내지 않는다.** `depends-on`·`superseded-by` 는 기계가 추론하지 않고, 에이전트가 노트를 읽고 직접 적는다.
- 새 노트가 자동으로 편입되게 전역 규칙과 노트 작성 스킬에 이 frontmatter 를 박아 둔다 — 규약만 두면 고아가 다시 쌓인다.

스키마·템플릿: [schema/SCHEMA.md](schema/SCHEMA.md) · [examples/vault](examples/vault)

## 질의·점검 도구

`tools/graph.py` — Python 표준 라이브러리만 사용. `--json` 을 붙이면 에이전트가 읽기 좋은 출력.

```bash
python3 tools/graph.py stats   <vault>                      # 노드·엣지·허브 수, 고아 비율
python3 tools/graph.py query   <vault> --domain payments    # 도메인 노트 + depends-on 으로 끌려오는 노트, 대체된 노트 표시
python3 tools/graph.py current <vault> 2026-01-10-checkout-v1-spec   # superseded-by 를 따라 현재 기준 노트
python3 tools/graph.py lint    <vault>                      # 끊긴 엣지 · 판정 불가 · related 사용 · 대체 순환
```

예제 vault 에서 `query --domain payments`:

```
- .../2026-01-20-idempotency-key-decision  [accepted]
- .../2026-03-02-checkout-v2-spec  [completed]
    depends-on .../2026-01-20-idempotency-key-decision
    depends-on .../orders/order-state-machine
    implements feature/checkout-v2 @ 3f2a91c
- .../2026-01-10-checkout-v1-spec  [superseded]  ⤳ superseded, current = .../2026-03-02-checkout-v2-spec
+ .../orders/order-state-machine  (pulled in by .../2026-03-02-checkout-v2-spec)
```

같은 이름의 노트가 여러 폴더에 있으면 `moc` 엣지는 허브를, 나머지는 링크를 건 노트와 경로가 가장 가까운 쪽을 고르고, 그래도 동률이면 "판정 불가"로 남긴다.

## 실제 vault 에 돌린 결과 (2026-11-03, 집계만)

| 항목 | vault 전체 | `projects/` 만 |
|---|---|---|
| 노트 | 1,418 | 894 |
| `domain` 있음 | 884 | 804 |
| MOC 허브 | 49 | 49 |
| 엣지 `moc` · `depends-on` · `superseded-by` | 682 · 929 · 60 | |
| `implements` 가 있는 노트 | 454 | |
| 고아 비율 | 18.8% (기억·산출물 폴더 포함) | 9.5% (도입 직후 4%) |

`lint` 가 찾은 실제 결함: 끊긴 엣지 13건 — Obsidian 이 해석하지 못하는 상대경로 링크(`[[../x]]`) 4건, 아직 만들지 않은 허브를 가리키는 `moc` 9건. 폐기한 `related` 필드가 남은 노트 24개.

## 에이전트 작업 규칙 (같이 쓰는 것)

| 경로 | 내용 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 전역 규칙 템플릿 — 근거 규칙 · 작업 방식 · 기록 위치 · 세션 인계 |
| [rules/evidence-required.md](rules/evidence-required.md) | 근거 없는 단정 금지 — 실제로 밟은 실패 사례 |
| [rules/solo.md](rules/solo.md) | 직접 작업 4원칙 (Andrej Karpathy 의 CLAUDE.md 가이드라인 기반) |
| [rules/mx-inline-markers.md](rules/mx-inline-markers.md) | 위험 지점 인라인 마커 4종 (MoAI-ADK `@MX` 어휘 차용) |
| [hooks/no-ai-attribution.sh](hooks/no-ai-attribution.sh) | commit-msg 훅 — AI 공동저자 문구가 있으면 커밋 거부 |
| [skills/](skills) | 명세 체인 `spec-docs → spec-review → spec-run → spec-verify`, 세션 인계 `handoff-out` · `handoff-in` |

## 한계

- frontmatter 파서는 YAML 일부(`key: value`, 인라인·블록 목록)만 읽는다.
- 엣지를 자동으로 만들지 않는다(의도). 엣지 품질은 노트를 쓰는 쪽의 규칙 준수에 달려 있다.
- Bases 자동 표는 Obsidian 화면용이다 — 에이전트는 `graph.py` 나 frontmatter 를 직접 읽는다.

회사 코드·내부 문서·서비스 이름은 들어 있지 않습니다. 예제 vault 는 가상의 결제 도메인으로 새로 만들었습니다.
