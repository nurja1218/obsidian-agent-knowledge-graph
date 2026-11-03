# claude-code-workflow

AI 코딩 에이전트(Claude Code)를 **근거 기반으로, 팀 규칙 안에서** 쓰기 위해 만든 개인 작업 체계의 템플릿입니다.
2026년 5월부터 매일 쓰는 설정에서 회사·개인 정보를 빼고 구조·규칙·스킬만 남겼습니다.

![구조](docs/structure.svg)

## 핵심 아이디어

1. **vault 하나가 원본** — Obsidian vault 안에 규칙·훅·스킬(`claude-config/`), 장기 기억(`memory/`), 작업 노트(`projects/`)를 두고 `~/.claude/` 는 심볼릭 링크로 가리킨다. 기기·계정이 달라도 같은 규칙으로 일한다.
2. **근거 없는 진술 금지** — 에이전트가 "그럴듯한 동작 모델"로 단정하던 실패를 표로 쌓고, 규칙으로 막는다 ([rules/evidence-required.md](rules/evidence-required.md)).
3. **도구 층에서 강제** — 지켜야 하는 규칙은 문서로 두지 않고 훅으로 건다. 문서로만 둔 도구는 결국 안 쓰였다.

## 들어 있는 것

| 경로 | 내용 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 전역 규칙 템플릿 — 근거 규칙 · 세 층 작업 방식 · 기록 위치 · 세션 인계 |
| [rules/evidence-required.md](rules/evidence-required.md) | 근거 없는 단정 금지 — 실제로 밟은 실패 사례와 체크리스트 |
| [rules/solo.md](rules/solo.md) | 직접 작업할 때 4원칙 (Andrej Karpathy 의 CLAUDE.md 가이드라인 기반) |
| [rules/mx-inline-markers.md](rules/mx-inline-markers.md) | 위험 지점 인라인 마커 4종 (MoAI-ADK `@MX` 어휘 차용) |
| [hooks/no-ai-attribution.sh](hooks/no-ai-attribution.sh) | commit-msg 훅 — AI 공동저자 문구가 있으면 커밋 거부 |
| [skills/spec-docs](skills/spec-docs/SKILL.md) | 요청 → 코드 분석 → 명세서 작성 (구현하지 않음) |
| [skills/spec-review](skills/spec-review/SKILL.md) | 여러 모델 교차 비판 2라운드로 명세 검토 |
| [skills/spec-run](skills/spec-run/SKILL.md) | 명세 단계별 실행 — 작업 격리(worktree) |
| [skills/spec-verify](skills/spec-verify/SKILL.md) | 구현 검증 — 명세 충족 + 품질 게이트, 라운드 상한 3 |
| [skills/handoff-out](skills/handoff-out/SKILL.md) · [handoff-in](skills/handoff-in/SKILL.md) | 세션 종료 시 인계서 작성 / 새 세션에서 인계서 내용을 실제로 열어 대조 |

## 설치

```bash
git clone https://github.com/nurja1218/claude-code-workflow.git ~/claude-code-workflow
ln -s ~/claude-code-workflow/CLAUDE.md ~/.claude/CLAUDE.md          # 기존 파일이 있으면 먼저 백업
ln -s ~/claude-code-workflow/rules ~/.claude/rules
ln -s ~/claude-code-workflow/skills ~/.claude/skills
ln -s ~/claude-code-workflow/hooks/no-ai-attribution.sh <레포>/.git/hooks/commit-msg
```

- 스킬 안의 `<vault>` 는 노트를 쌓을 폴더 경로로 바꿔 읽으면 된다.
- 교차 리뷰 스킬은 여러 모델을 부르는 MCP(예: ai-cli)를 전제로 한다 — 없으면 Claude 단독으로 같은 절차를 밟는다.

## 실제로 쓰며 생긴 규칙들 (예)

| 무슨 일이 있었나 | 그래서 생긴 규칙 |
|---|---|
| 배포 시간 증가 원인을 커밋 하나로 단정 → 단계별 수치를 보니 그 단계만 안 늘었다 | 총량 변화는 구성요소별로 배분하지 못하면 "원인"이 아니라 "후보" |
| 검색 결과 0건을 "없음"으로 결론 → 셸 수식자·바이너리 판정 때문에 명령이 깨져 있었다 | 부정 결과는 다른 방법으로 한 번 더 확인 |
| 세션 지시가 팀 커밋 규칙(AI 문구 금지)을 뒤집고 커밋 14개에 문구가 붙었다 | 문서가 아니라 commit-msg 훅으로 거부 |

## 공개 범위

회사 코드·내부 문서·서비스 이름은 들어 있지 않습니다. 규칙 문서의 실패 사례도 일반 표현으로 바꿨습니다.
