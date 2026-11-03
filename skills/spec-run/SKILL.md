---
description: 명세서 Phase를 3-Layer 배정에 따라 실행. ai-cli-mcp worktree 격리 + Semantic Contract.
argument-hint: "명세서 경로 (생략 시 가장 최근 명세서 자동 탐지)"
---

# /spec-run — 구현 실행 (Operations Layer)

명세서의 Phase를 배정에 따라 실행한다. 워커 선택은 자동. 사용자가 도구를 직접 지정하지 않는다.

글로벌 3-Layer 매핑: 이 단계는 **Operations Layer** — Layer 1(Main Solo)과 ai-cli-mcp worktree 격리를 결합. S급·1~2파일 R급은 Layer 1, 3+파일 R급은 worktree 격리(Semantic Contract). 그라운딩이 필요한 phase는 Layer 2 병렬도 가능.

모든 출력은 **한국어**로 한다.

---

## Step 0: 프로젝트 컨텍스트 로드

`.claude/config/project-context.yaml` 있으면 → `project_domains`, `verify_commands`, `worker_extra_rules` 사용.
없으면 → default 폴백:
- `verify_commands`: `package.json` scripts에서 `type-check|typecheck`, `lint`, `test` 키 자동 탐색
- `worker_extra_rules`: `.claude/rules/*.md` 자동 감지 (있으면 워커 프롬프트에 인용)
- `agents_md_path`: `AGENTS.md` 자동 감지 (있으면 §3 등 검토 기준 인용)

---

## Step 1: 명세서 로드 + Phase 파싱

1) 인자로 명세서 경로 주어지면 해당 파일 Read
2) 없으면 `docs/`, vault `specs/`, 또는 yaml로 명시된 디렉토리에서 가장 최근 수정된 명세서 자동 탐지
3) Phase 목록, 복잡도(S/R), 배정 정보 파싱
4) 사용자에게 실행 계획 제시 + **컨펌**

```
━━━ 구현 실행 계획 ━━━

명세서: {경로}

실행 순서:
  Phase 1 (S급)        → Main 직접 (Layer 1)
  Phase 2 (R급, 1파일) → Main 직접 (Layer 1)
  Phase 3 (R급, 4파일) → ai-cli-mcp worktree sonnet (Semantic Contract)
  Phase 4 (R급, 그라운딩 필요) → Layer 2 병렬: sonnet + gemini-2.5-flash

승인하면 실행을 시작합니다.
```

---

## Step 2: Phase별 실행

**🧰 도구 연동 (구현 중, MoAI 이식):**
- 위험/계약 지점(publishAll·DDB↔PG converter·ChatRoomStore·fan-in≥3·fire-and-forget)에 `@MX` 부착 — `npx tsx ~/.claude/tools/mx/cli.ts` 로 규약 참조, 애매하면 `mx` attach 로 P1/P2 후보 자동 제안. (워커 프롬프트에 "위험 지점은 @MX 로 표기" 지시)
- 빌드/테스트 출력이 크면 `npx tsx ~/.claude/tools/verify/cli.ts run "<cmd>" --root <repo>` 로 다이어트(exit+tail 50만 컨텍스트, 전체는 스냅샷).

### Phase 결과 보고 4항목 (모든 Phase 공통, 필수)

배정(Main 직접 / 워커)과 무관하게 Phase 가 끝나면 아래 4항목을 남긴다. 워커 Phase 는 `.work/semantic/{phase}.report.md` 에, Main 직접 Phase 는 사용자 보고와 명세서 해당 Phase 끝의 `### 결과` 에 쓴다. 리뷰하는 사람이 diff 전체를 읽지 않고도 판단할 수 있게 하기 위함이다.

1. **변경 이유** — 명세의 어느 요구·완료 기준 항목을 위한 변경인가
2. **영향 범위** — 바뀐 파일과, 이 변경에 영향받는 호출자·API·데이터
3. **검증 결과** — 실행한 명령과 결과(통과/실패 수), 완료 기준 항목별 판정
4. **남은 위험** — 확인 못 한 것, 알려진 한계, 다음 Phase·사람이 볼 것. 없으면 "없음"

### S급 Phase → Main 직접 (Layer 1 Solo)
- Main이 코드를 직접 수정
- 완료 후 `verify_commands` 실행하여 증거 남김
- 결과 보고 4항목 작성 (위)

### R급 Phase (1~2파일) → Main 직접 (Layer 1 Solo)
- Main이 코드를 직접 수정 (worktree 격리 가치 없음, 오버헤드 회피)
- 완료 후 diff 확인 + verify 명령 실행
- 결과 보고 4항목 작성 (위)

### R급 Phase (3파일+) → ai-cli-mcp worktree (Operations + Semantic Contract)

**모델 선택:**
- 기본: `sonnet`
- 코드 디테일/테스트 중심: `gpt-5.3-codex`
- 그라운딩(라이브러리 변경 추적) 필요 시 → Layer 2 병렬로 격상 (아래)

Semantic Contract 워크플로우 (10단계, **`.work/semantic/` 산출물 필수**):

```
1. worktree 생성
   git worktree add ../_w/{phase} -b w/{phase}

2. 워커 프롬프트 생성 (표준 템플릿 기반)
   필수 섹션 (생략 금지):
   - [Semantic Spec]      : 명세서 전문 인용
   - [Canonical Terms]    : 용어 사전 (재정의 금지)
   - [Phase Contract]     : Allowed/Forbidden Files·Operations
   - [Contract 보고 의무] : 워커는 코드 수정 전 .work/semantic/{phase}.interpretation.md,
                            수정 후 .work/semantic/{phase}.report.md 작성
   - [Surgical Changes Rule] (카파시 §2/§3 적용 — 과설계 방지):
       · 변경 line마다 [Semantic Spec] 요청 + [Phase Contract] Allowed Files에 *직접 추적 가능*해야 함.
       · 명세 외 추상화·"유연성"·"설정 가능성" 추가 금지.
       · 인접 코드 "개선"·refactor·포맷팅 정리 금지 — 기존 스타일 유지.
       · 자기 변경이 만든 orphan만 정리. 사전 dead code는 .report.md에 *언급만*, 삭제 금지.
       · "선배 엔지니어가 over-complicated이라 할까?" 자문 후 단순화.
       · "더 견고하게 만들고 싶다" 같은 명세 외 욕심 금지 — Acceptance Criteria 안에서만.
   - [프로젝트 룰] (yaml `worker_extra_rules` 또는 `.claude/rules/*` 자동 감지 시 인용):
       · 해당 파일들의 BLOCKER·필수 패턴을 명시적으로 워커에 노출.

3. ai-cli-mcp.run() → 워커 스폰
   workFolder는 반드시 worktree 경로 (메인 디렉토리 금지, P0)

4. ai-cli-mcp.wait() → 결과 수집

5. 품질 게이트 1회차 (merge 전, worktree에서)
   verify_commands 실행 (type_check, lint)
   → 실패 시 워커에 재작업 또는 Main 수정

6. Semantic Review (merge 전, 필수)
   → .work/semantic/{phase}.interpretation.md 존재 + Canonical Terms 일관성 확인
   → .work/semantic/{phase}.report.md 존재 + Phase Contract 준수 확인
   → 누락 시 워커에 재작업 요청 (보고서 없이 merge 금지)
   → 병렬 워커 2+일 때: Consistency Gate (interpretation 차이 비교)

7. git merge --no-ff w/{phase} -m "merge: Phase {N}"

8. 품질 게이트 2회차 (merge 후)
   verify_commands 실행

9. 코드 리뷰 (선택)
   프로젝트에 `code-reviewer` 서브에이전트 정의되어 있으면 호출.
   없으면 Main이 receiving-code-review 원칙으로 리뷰.

10. (worktree 정리는 사용자 재량 — 자동 정리 안 함)
    재작업 가능성·디버깅 가치 있어 보존이 기본.
    수동 정리 시: git worktree remove ../_w/{phase} && git branch -d w/{phase}
```

### R급 Phase + 그라운딩/긴 컨텍스트 → Layer 2 병렬
다양성이 필요한 phase는 worktree 격리 대신 (또는 추가로) Layer 2 병렬:
- `mcp__ai-cli__run` 2~3개 PID 동시 발사: `sonnet` + `gemini-2.5-flash` (+ `gpt-5.3-codex` 가능 시)
- 두 결과 비교 → 차이점 합성 → Main이 최종 결정
- Self-anchoring 방지: gemini 결과를 *먼저* 읽고 자기 첫 답과 차이 분석

### 폴백 체인
도구 사용 불가 시 자동 전환 (Graceful Degradation):
```
ai-cli-mcp sonnet → gemini-2.5-flash → gpt-5.3-codex → 내장 서브에이전트 → Main 직접
```
gemini-2.5-pro는 quota 한정적 — 명세상 명시되지 않으면 호출 금지 (flash 우선).

---

## Step 3: 완료 검증 (verification-before-completion 원칙)

**🧰 도구 연동 (Phase/전체 완료 시, MoAI 이식):** tsc/lint 0 확인을 도구로:
- 빠른 게이트: `npx tsx ~/.claude/tools/verify/cli.ts gate <repo> --no-test` (typecheck+lint 병렬 pass/fail, 재실행은 스냅샷 재사용).
- green 까지 자동수정: `npx tsx ~/.claude/tools/ralph/cli.ts run <repo> --loop --autofix` (Level-1 기계적 정리 후 남은 Blocker 는 LLM 이 수정).

**완료를 주장하기 전에 반드시 검증 명령을 실행하고 증거를 제시한다.**

- yaml `verify_commands` 기반 실행 (예: `npx tsc --noEmit`, `pnpm lint`, `npm test`)
- "통과할 것이다", "문제없을 것이다" 같은 추측 금지
- 명령 실행 → 출력 확인 → 결과 제시
- 에러가 있으면 수정 후 재검증

---

## Step 4: 결과 제시

```
━━━ 구현 완료 ━━━

변경 파일:
  - {파일 경로 1}
  - {파일 경로 2}

검증:
  type_check: 0 errors
  lint: 0 errors

Phase별 결과 (4항목):
  Phase 1 — 변경 이유: … / 영향 범위: … / 검증 결과: … / 남은 위험: …

다음 단계:
  → /spec-verify 로 코드 검증
  → /git-commit 으로 바로 커밋
```

$ARGUMENTS
