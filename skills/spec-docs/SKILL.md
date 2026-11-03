---
description: Layer 2 Discovery — 사용자 요청 → 코드베이스 분석 → 명세서 생성 → Phase별 3-Layer 배정. 구현은 하지 않는다.
argument-hint: "구현하고 싶은 기능을 자유롭게 설명"
---

# /spec-docs — 명세서 생성 (Layer 2 Discovery)

사용자가 자연어로 요청하면, 코드베이스를 분석하여 실행 가능한 명세서를 생성한다. **구현은 하지 않는다** — 구현은 `/spec-run`에서.

글로벌 3-Layer 매핑: 이 단계는 **Layer 2 (Parallel Diversity / Discovery)**. 그라운딩·긴 컨텍스트 분석이 필요한 phase는 `gemini-2.5-flash` 병렬로 다양성 확보.

모든 출력은 **한국어**로 한다.

---

## Step 0: 프로젝트 컨텍스트 로드 (자동)

작업 디렉토리에서 다음을 *순서대로* 시도하여 프로젝트 컨텍스트 확보:

1. **`.claude/config/project-context.yaml` 존재하면** → 그 내용을 컨텍스트 기준으로 사용
2. **yaml 없으면 → 자동 감지 폴백**:
   - `project_domains` 기본값: 작업 디렉토리 직속 `src/`, `app/`, `apps/`, `lib/`, `packages/` 중 *실제 존재하는 것*
   - `verify_commands` 기본값: `package.json` scripts에서 `type-check|typecheck`, `lint` 키 자동 탐색
   - `rules_dir`: `.claude/rules/` 존재 시 자동 적용
   - `agents_md_path`: `AGENTS.md` 또는 `agents.md` 존재 시 자동 적용

project-context.yaml 스키마 참고 (있다면 `~/.claude/skills/spec-docs/CONTEXT.md`).

---

## Step 1: 분석 (자동)

**🧰 도구 연동 (권장, MoAI 이식):**
- `npx tsx ~/.claude/tools/codemap/cli.ts <repo> --app <앱>` → 대상 앱 아키텍처·모듈·WS path 계약·순환 의존성·**fan-in ANCHOR 후보**를 baseline 으로 확보. 재스캔 대신 이 맵 위에서 분석.
- `npx tsx ~/.claude/tools/mx/cli.ts query <repo> --kind ANCHOR` / `--danger` → 이미 표시된 계약·위험 지점을 명세 Phase Contract·BLOCKER 에 반영.

1) 사용자 요청에서 핵심 키워드 추출
2) 관련 코드 탐색 — `project_domains` 기반 병렬 탐색 (`Glob` + `Grep`)
3) 영향 범위 파악:
   - 수정 대상 파일 목록
   - 의존성 체인 (어떤 모듈이 영향받는지)
   - 기존 패턴 (동일 도메인 레퍼런스 코드)

> 보조 도구: 프로젝트에 `parallel-explore`, `serena` 같은 스킬·MCP가 정의되어 있으면 활용. 없으면 `Glob`/`Grep`만 사용.

---

## Step 2: 명세서 생성 (자동, 도메인 폴더 분리)

분석 결과를 바탕으로 명세서를 생성한다. **도메인별 폴더로 분리하여 vault에 누적 관리한다.**

### Step 2-1: 도메인 자동 추론

Step 1에서 발견된 코드 경로들에서 *주된 도메인* 1개를 추론한다.

추론 규칙:
1. yaml `project_domains` (예: `apps/api/src`)의 *서브디렉토리 첫 단계*를 도메인 후보로 본다
   - 예: `apps/api/src/order/order.entity.ts` → 도메인 `order`
   - 예: `apps/api/src/realtime/chat/single/handler.ts` → 도메인 `realtime` (또는 더 좁히면 `realtime-chat-single`)
2. 여러 도메인에 걸친 경우 *가장 많은 파일이 위치한 도메인* 1개 선택
3. 모노레포 패턴 (`apps/<app>/src/<domain>/...`)이면 *`<domain>`* (서비스 안 하위 도메인)을 우선
4. 단일 패턴 (`src/<domain>/...`)이면 그 `<domain>` 자체

### Step 2-2: 베이스 위치 결정 (항상 vault)

**모든 spec은 vault에 저장한다.** `docs/` 같은 repo 내 폴백은 사용하지 않는다 — 사용자 요구사항: 모든 spec → vault.

**(a) vault 라우팅 매핑 프로젝트** (글로벌 `~/.claude/CLAUDE.md` vault 라우팅 표에 명시):
- 베이스: `<vault>/projects/<repo-name>/specs/`
- `<vault>` 해석은 글로벌 `~/.claude/CLAUDE.md` "Vault 경로 동적 해석" 섹션 참조 (요약: `realpath ~/.claude/CLAUDE.md` 의 dirname 두 번).
- `<repo-name>` = cwd의 마지막 디렉토리명 (예: `my-service-2`)
- 자동 사용, 사용자 확인 없음

**(b) 미매핑 프로젝트** (예: 별도 레거시 레포):
- **동적 라우팅 발동** (글로벌 CLAUDE.md "동적 라우팅" 규칙 적용):
  1. 사용자에게 1회 확인: *"이 프로젝트의 spec도 vault(`<vault>/projects/<repo-name>/specs/`)에 둘까요?"*
  2. OK → 폴더 자동 생성 + 이후 자동 라우팅 (글로벌 CLAUDE.md 라우팅 표에 추가 제안)
  3. 거절 → 사용자가 명시한 경로 사용. 다음 세션에 다시 묻지 않도록 라우팅 표 "exclude" 추가 제안

베이스 디렉토리 내 *기존 도메인 폴더 목록*을 조회한다:
- 추론된 도메인과 매칭 폴더 있으면 → 그 폴더 사용 (사용자 확인 *생략*)
- 매칭 폴더 없으면 → Step 2-3

### Step 2-3: 새 도메인 발견 시 사용자 확인 (1회)

매칭 폴더가 없을 때만:
```
이 작업은 '<X>' 도메인으로 보입니다.
새 폴더 `<specs base>/<X>/`를 만들고 거기에 명세서를 생성할까요?

(다른 도메인이면 명시해주세요 — 예: 'chat-room' 대신 'message')
```

- OK → 폴더 자동 생성 + 거기 작성
- 사용자가 다른 도메인 명시 → 그 도메인 폴더 사용 (없으면 생성)

### Step 2-4: 파일명 규칙

도메인 폴더 결정 후:
- 티켓 번호가 있으면: `<TICKET>-<설명>.md` (예: `PROJ-123-message-pipeline.md`)
- 없으면: `<NN>-<주제>.md` (*해당 도메인 폴더 내* 기존 최대 번호 + 1, 전역 번호가 아님)

### 명세서 포맷 (필수 섹션)

```markdown
---
title: {제목}
created: {YYYY-MM-DD}
status: draft
domain: {추론된 도메인}
moc: "[[{추론된 도메인}]]"
tags: [spec, {domain}, ...]
implements: {현재 브랜치}
---
```

> typed-edge 규약(글로벌 `~/.claude/CLAUDE.md` "Vault typed-edge 지식그래프 규약"): 위 `moc`/`implements`는 기본 첨부. 관계 있으면 `depends-on: ["[[..]]"]` / 대체 시 `superseded-by: "[[..]]"` 추가. 무지 `related` 금지, 없는 관계 지어내기 금지. 도메인 MOC(`_meta/moc/<domain>.md`) 없으면 생성 제안.

```markdown

# {제목}

> 버전: 1.0 | 상태: 초안 | 브랜치: {현재 브랜치} | 도메인: {domain}

## 요약
{사용자 요청을 1~2문장으로 정리}

## 확정사항
| 결정 | 이유 |
|------|------|

## Canonical Terms (용어 사전)
| 용어 | 정의 | 금지 동의어 |
|------|------|------------|

> Canonical Terms는 이 명세서 내에서 절대 기준이다.
> 워커는 이 용어를 임의로 재정의하거나 다른 단어로 대체할 수 없다.

## Phase 1 -- {제목}
- **복잡도**: S 또는 R
- **배정**: Main 직접 (Layer 1) / ai-cli-mcp worktree sonnet / Layer 2 병렬 (sonnet + gemini-2.5-flash)
- **Spec Revision**: {YYYY-MM-DD.N}

### Phase Contract
Allowed Files:
- {파일 경로 1}

Forbidden Files:
- {프로젝트 고유 금지 파일 — yaml의 worker_extra_rules 참조}

Allowed Operations:
- {허용 작업}

Forbidden Operations:
- 다른 Phase 책임 영역 수정
- public API 시그니처 변경 (명세서에 명시된 경우 제외)
- DB schema 변경 (명세서에 명시된 경우 제외)

### 완료 기준 (이 Phase 가 "끝났다"의 판정)
| # | 기준 (관찰 가능한 결과) | 확인 방법 (명령 · 화면 · 데이터) |
|---|------|------|
| AC1 | {예: 메시지 저장 후 방 목록 정렬이 최신순} | {예: `pnpm test order` 통과 / dev 화면 스크린샷 / 조회 쿼리 결과} |

사람 승인 지점: {사람이 직접 확인·승인해야 하는 것. 없으면 "없음"}

> 테스트로 못 재는 품질(UI·문서·프롬프트 응답)은 "좋아 보임" 대신 구체 기준으로 쓴다 — 필수 화면 상태·스크린샷, 필수 항목·용어, n회 실행 중 통과 횟수 등.

### Before / After / 검증
{기존 코드, 변경 코드, 검증 체크리스트}

## Phase N -- ...
```

---

## Step 3: 워커 배정 (자동, 3-Layer 매핑)

| 복잡도 | 조건 | 배정 | 글로벌 Layer |
|--------|------|------|------------|
| S급 (설계·동시성·크로스앱·외부 통합) | — | Main 직접 | Layer 1 |
| R급 | 1~2파일 | Main 직접 | Layer 1 |
| R급 | 3파일+ | ai-cli-mcp worktree (sonnet) + Semantic Contract | Operations |
| R급 + 그라운딩/긴 컨텍스트 (라이브러리 변경 추적, 대규모 readthrough) | — | Layer 2 병렬: sonnet + gemini-2.5-flash | Layer 2 |
| R급 + 코드 디테일·테스트 중심 | — | ai-cli-mcp worktree (gpt-5.3-codex) | Operations |
| 도구 전부 실패 | — | Main 직접 | Layer 1 |

배정 규칙:
1. S급 Phase → Main 직접 구현
2. R급 1~2파일 → Main 직접 (worktree 격리 가치 없음, 오버헤드 회피)
3. R급 3+파일 → ai-cli-mcp worktree (Semantic Contract 필수)
4. 그라운딩/긴 컨텍스트 → Layer 2 병렬로 다양성 확보
5. 같은 파일 수정 → 순차 (충돌 방지)
6. 동시 PID 최대 3개

---

## Step 4: 사용자에게 결과 제시

```
━━━ 명세서 + 작업 배정 ━━━

명세서: {경로}

Phase 배정:
  Phase 1 (S급)          → Main 직접 (Layer 1)
  Phase 2 (R급, 1파일)   → Main 직접 (Layer 1)
  Phase 3 (R급, 4파일)   → ai-cli-mcp worktree sonnet (Semantic Contract)
  Phase 4 (R급, 그라운딩 필요) → Layer 2 병렬: sonnet + gemini-2.5-flash

다음 단계:
  → /spec-review 로 설계 검증
  → /spec-run 으로 바로 구현
```

사용자 피드백 있으면 명세서 수정 + 반복. **사용자가 만족할 때까지 구현 시작 안 한다.**

---

## Step 5: 티켓 제안 (팀 레포일 때만, 1줄)

명세가 확정된 시점이 티켓 요약·작업내용이 가장 정확한 시점이다. 명세 제시 후 **한 줄만** 덧붙인다:

```
  → 티켓을 만들까요? (현재 브랜치에 티켓 키 없음)
```

- 브랜치명에 이미 `[A-Z]+-\d+` 키가 있으면 **묻지 않는다**
- ⛔ 자동 생성 금지 — 사용자 승인 후에만

$ARGUMENTS
