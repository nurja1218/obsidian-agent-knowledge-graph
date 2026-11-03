---
description: Layer 3 구현 검증 — ai-cli-mcp Cross-Critique 2-Round (debate + security framing). 명세 충족 + 코드 품질 심층 리뷰.
argument-hint: "명세서 경로 (생략 시 가장 최근 명세서 자동 탐지)"
---

# /spec-verify — 구현 코드 검증 (Layer 3 구현 Adversarial)

구현된 코드를 명세서 대비 검증하고, 프로젝트 품질 기준으로 심층 리뷰한다.
**수정사항이 없을 때까지 반복한다.**

글로벌 3-Layer 매핑: 이 단계는 **Layer 3 (Adversarial Review)** — 구현 단계의 약점을 *적대적 framing*으로 노출. 패턴 B(Cross-Critique 2-Round) + 별도 security framing 호출로 다른 모델 시각 도입.

> 도구: `mcp__ai-cli__run` 다중 PID 병렬 호출.
>
> **Graceful Degradation:** 3 PID(sonnet + gemini-2.5-flash + gpt-5.3-codex) 발사 후 실패 PID(예: codex vendor ENOENT)는 자동 제외. Round 2 cross-critique도 살아있는 답끼리만. 작업 안 멈춤. 2개 이상 실패 시 Main 보고 후 단순 검토로 폴백.

모든 출력은 **한국어**로 한다.

> receiving-code-review 원칙 적용:
> 리뷰 결과에 "Great!", "Good catch!" 등 감정 표현 금지.
> 기술적 사실만 진술하고, 수정하거나 근거를 들어 반박한다.

---

## Step 0: 프로젝트 컨텍스트 로드

`.claude/config/project-context.yaml` 있으면 → `verify_commands`, `rules_dir`, `agents_md_path`, `review_checklist_section`, `project_blockers` 사용.
없으면 → default 폴백 (자동 감지: `.claude/rules/*.md`, `AGENTS.md`, `package.json` scripts).

---

## Step 1: 변경사항 수집

1) 명세서 로드 (인자 또는 자동 탐지)
2) 변경사항 수집:
   ```bash
   git diff --name-only    # 변경 파일 목록
   git diff                # 상세 변경 내용
   git diff --cached       # staged 변경
   ```
3) 변경 파일 내용을 깊이 읽는다 (diff만이 아니라 전체 맥락)

---

## 리뷰 워커 쓰기 금지 (Step 2~4 의 모든 ai-cli 호출 공통, 필수)

리뷰 워커는 파일 쓰기 권한이 있어서 "검토만" 시켜도 코드를 고칠 수 있다 (2026-09-10 이 스킬 Round 2 에서 실측 — 메모리 `ai-cli-worker-writes-during-review`).

1. **호출 전 기준선**: `git status --porcelain` 출력과 `git diff | shasum` 값을 저장한다.
2. **모든 리뷰 프롬프트 맨 앞에 고정 문구**: "⛔ 파일을 만들거나 수정·삭제하지 마라. 상태를 바꾸는 명령을 실행하지 마라. 판정과 근거(파일:줄)만 텍스트로 출력하라."
3. **각 `wait` 직후**: 같은 두 값을 다시 떠서 기준선과 비교한다.
   - 기준선에 없던 파일이 바뀌었거나 새로 생겼으면 → 워커가 만든 변경이다. 파일 목록을 사용자에게 알리고 되돌린다 (`git checkout -- <파일>`, 새 파일은 삭제).
   - 기준선에 이미 있던 파일의 diff 값이 달라졌으면 → 구현 중인 미커밋 변경과 섞여 자동으로 되돌릴 수 없다. **멈추고 사용자에게 보고**한다.
   - 지적 내용 자체는 결과에 기록으로 남긴다 (범위 밖이면 해당 Phase 로 넘긴다).
4. 예상 밖 변경을 정리하기 전에는 다음 Round 를 시작하지 않는다.

---

## Step 2: Cross-Critique Round 1 — Debate framing (필수, 병렬 3 PID)

git diff + 변경 파일 전체 맥락을 prompt에 포함하여 3개 모델에 동시 호출. 각 모델은 *서로의 답을 모르는 채* 독립 의견 (blinded).

```
mcp__ai-cli__run × 3 PID 동시:
  - sonnet            (Claude 시각, 설계·전반)
  - gemini-2.5-flash  (Gemini 시각, 그라운딩·다른 분포)
  - gpt-5.3-codex     (Codex 시각, 코드 디테일)
workFolder=repo root, prompt에 명세서 + diff + 변경 파일 본문 포함

→ wait([3 pids], timeout=180) → get_result → answer_A/B/C
```

**Framing (반드시 적대적):**
- "이 구현이 프로덕션에서 6개월 후 실패한다면 가장 가능성 높은 시나리오 3개"
- "이 변경의 가장 큰 trade-off, 놓친 엣지케이스"
- "더 단순한 해결책이 있는데 과설계 된 부분, 또는 더 견고해야 하는데 단순화한 부분"
- "성능·정합성·확장성 중 가장 약한 축"

---

## Step 3: Cross-Critique Round 2 — Mutual Critique (필수, 병렬 PID 살아있는 답끼리)

Round 1의 답들을 *교차*로 모델들에게 보여주고 반박하게 한다.

```
mcp__ai-cli__run × {살아있는 PID 수} 동시 (각자 *다른 답*을 prompt에 포함):
  - sonnet  ← {answer_B, answer_C} 받고 "B와 C의 약점·반박" → 비판 A'
  - gemini  ← {answer_A, answer_C} 받고 "A와 C의 약점·반박" → 비판 B'
  - codex   ← {answer_A, answer_B} 받고 "A와 B의 약점·반박" → 비판 C'

→ wait → get_result
```

**메타인지 강제 (답이 수렴할 때 특히):**
> "두 답이 같은 결론으로 수렴했다면 — 정답의 증거인가, 질문 framing의 bias인가? 비판하라."

---

## Step 4: Security framing 호출 (필수, 병렬 PID — 별도 1 round)

코드 수준 보안 검토 — debate와는 framing이 달라 별도 호출.

```
mcp__ai-cli__run × 3 PID 동시 (security framing):
  - sonnet
  - gemini-2.5-flash
  - gpt-5.3-codex (보안 framing은 코드 디테일 강점 가치 큼)
workFolder=repo root, prompt에 변경 파일 본문 + 프로젝트 BLOCKER 룰 (yaml `project_blockers` 또는 `.claude/rules/*` 자동 감지)
```

**Security framing prompt 항목:**
- OWASP Top 10 (인젝션, broken auth, sensitive data exposure, XXE, broken access, security misconfig)
- 인증/권한 로직 우회 가능성
- 입력 검증 누락 (특히 외부 경계, 케이스 변환 지점)
- 에러 정보 노출 (스택, 내부 경로, 사용자 식별)
- SQL 인젝션, XSS, CSRF, SSRF
- 민감 데이터 로깅
- 프로젝트 고유 BLOCKER (yaml `project_blockers` 인용)

---

## Step 5: 심층 검토 (Main이 직접) — 프로젝트 기준 적용

**검토 기준 출처 (자동 결정):**
- yaml `agents_md_path` + `review_checklist_section` 있으면 → 그 본문 적용
- 없으면 → `AGENTS.md` 자동 감지, `.claude/rules/*.md` 전체 적용
- 둘 다 없으면 → 보편 베스트 프랙티스 적용

### A. 프로젝트 기준 적용 (DRY — AGENTS.md / rules가 *기준*, spec-verify가 *실행*)
프로젝트가 제공한 규칙 목록을 변경 코드에 적용:
- 네이밍·구조 컨벤션
- 타입 안전성·에러 처리 패턴
- 아키텍처 계층 위반
- 프로젝트 고유 BLOCKER

### B. 명세 충족 + 품질
1. **명세 목적 달성** — Phase 별 "완료 기준" 표의 각 항목을 그 행의 확인 방법대로 판정한다 (항목별 PASS/FAIL + 근거).
   - "완료 기준" 표가 없는 명세(2026-10-29 이전 템플릿)는 → 그 Phase 의 "Before / After / 검증" 체크리스트로 판정하고, 결과에 "완료 기준 표 없음 — 검증 항목으로 대체" 1줄을 남긴다. **표가 없다는 이유만으로 BLOCKER 처리 금지.**
2. **Phase Contract 준수** — Allowed/Forbidden 위반 없음
3. **Canonical Terms 일관성** — 명세서 용어가 코드에서 일관되게 사용
4. **과설계 기피** — 한 번만 쓰이는 추상화, 불필요한 제네릭, premature abstraction
5. **Dead code** — 사용 안 되는 import/변수/함수, 주석 처리 코드, 도달 불가
6. **베스트 프랙티스** — 타입 안전성(as 지양), 성능(N+1 회피), 로깅 적절성
7. **Surgical Changes 추적성 (카파시 §3)** — *모든 변경 line이 명세 요청·Phase Contract Allowed에 직접 추적 가능한가?*
   - 추적 안 됨 = 군더더기 → [WARNING]
   - 명세 외 추상화·refactor·인접 코드 정리 = [BLOCKER]
   - 자기 변경 외 사전 dead code는 *언급만* 가능, 같은 PR에서 삭제 금지 (별도 제안으로 분리)
   - diff line별로 "이 line이 어느 명세 항목을 위한 것?"이 답 가능해야 함

---

## Step 6: 결과 제시 (Main 합성, self-anchoring 방지)

**합성 순서 (필수):**
1. *외부 의견을 먼저 읽고 요약* — Main이 자기 결론 형성 전에 다 흡수
2. 공통 약점 추출 (3+ 모델 동의 = high confidence)
3. 의견 갈리는 지점 (1~2 모델만 지적 = 검토 필요)
4. Step 5 자체 검토와 *차이점*만 보고
5. **프로젝트 Anchor 강제** (글로벌 룰 `프로젝트 Anchor 원칙` 적용): 외부 답의 일반론 표현을 *변경 파일 경로·diff 라인 번호·실제 함수·클래스명·테이블·API*로 변환해 재기술. anchor 못 한 지적은 "코드에서 확인 안 됨 — 사용자 검토 필요" 명시. 공통 약점·의견 갈림·BLOCKER/WARNING 모든 항목에 적용.
   - ❌ "에러 처리 누락 우려" → ✅ "`chat.service.ts:87` 의 `sendMessage`에서 `await this.repo.save()` 의 throw catch 없음 — `socket.gateway.ts:140` 에서 unhandled rejection 가능"

```
━━━ 코드 검증 결과 ━━━

명세서: {경로}

Cross-Critique (debate framing):
  Round 1 — sonnet/gemini/codex 독립 의견 요약
  Round 2 — 교차 비판으로 노출된 약점

Security framing:
  - [모델별 우려 사항, ⛔ BLOCKER 우선]

공통 약점 (high confidence):
  1. ...

의견 갈리는 지점:
  1. ...

프로젝트 기준 + 명세 충족 검토 (Main 직접):
  [BLOCKER] ...
  [WARNING] ...
  [PASS] ...

수정 필요:
  1. {파일:라인} — {내용}

수정 불필요:
  → PASS: 코드 검증 완료. /git-commit 으로 진행 가능.
```

---

## Step 6-1: 리뷰 지적 판정 기록 (필수, 명세서 끝에 추가만)

리뷰어(모델들·Main)의 지적이 실제로 맞았는지를 쌓아, 어느 모델·질문 방식이 헛지적을 많이 내는지 나중에 볼 수 있게 한다. 여러 모델이 동의했다는 것만으로 맞다고 보지 않기 위한 기록이다.

명세서 맨 끝에 아래 표가 없으면 만들고, 있으면 **행만 추가**한다 (기존 행 수정·삭제 금지). 처리 결과는 Step 7 에서 사용자가 결정한 뒤 채운다.

```markdown
## 리뷰 지적 기록

| 날짜 | 라운드 | 출처 | 지적 (파일:줄) | 처리 | 사유 |
|------|--------|------|----------------|------|------|
| (예시) 2026-10-29 | R1 | gemini | `chat.service.ts:87` save 예외 미처리 | 채택 | 재현됨 |
```

- 출처 = 처음 지적한 쪽 (`sonnet` / `gemini` / `codex` / `security:<모델>` / `Main`). 여러 모델이 같은 지적이면 `sonnet+gemini` 처럼 함께 쓴다.
- 처리 = `채택`(고침) / `기각`(맞는 말이지만 이번 범위·결정상 안 고침) / `오탐`(코드 확인 결과 틀린 지적) / `보류`(사용자 판단 대기).
- 사유는 한 줄. `오탐` 은 무엇을 확인해서 틀렸다고 봤는지 쓴다.

---

## Step 7: 수정 반복

수정 필요 사항이 있으면:
1. 사용자에게 제시 → 확인 후 코드 수정
2. 수정 후 검증 (verification-before-completion 원칙):
   - yaml `verify_commands` 실행 (예: `npx tsc --noEmit`, `pnpm lint`)
   - 0 errors 확인
3. Step 2~6 재실행
4. BLOCKER 0건 + WARNING 0건(또는 사용자 무시 확인) 될 때까지 반복

### 수렴 게이트 (완료 기준 — 도구로 자동 판정)

**🧰 실제로 도는 명령 (2026-08-04 실측 기준):**
1. **검증 명령은 raw 로 돌리지 말 것** — `npx tsx ~/.claude/tools/verify/cli.ts run "<verify_commands 의 명령>"`.
   전체 출력은 `.verify/snapshots/` 로 가고 exit + tail 50줄만 남으며, 워킹트리 해시가 같으면 재실행 없이 재사용된다(라운드를 돌수록 이득). 글로벌 PreToolUse 훅도 같은 유도를 한다.
2. **`npx tsx ~/.claude/tools/mx/cli.ts validate <repo> --files <변경파일>`**
   → **baseline 래칫 기준**이다. 레포의 기존 부채(`.mx/mx-baseline.json`)는 통과하고, **이번 변경이 새로 만들었거나 악화시킨 위반만** 뜬다. 전체 현황을 보려면 `--no-baseline`.
   → 여기서 뜨는 P1/P2 는 "내가 만든 것"이므로 **면제 없이 해소하거나 마커를 붙인다.**
3. **DEBT rot**: `mx scan <repo>` (색인 생성 — 안 하면 `색인 없음` 으로 끝난다) → `mx query <repo> --rot`.

**⛔ 설정 없는 레포에서 쓰지 말 것:**
- `ralph run --json` — `ralph.config.json` 이 없으면 기본 설정으로 오판한다.
- `verify gate` — 기본값이 루트 전체 lint·test 라 큰 모노레포에는 비현실적.

반복이 "언제 끝났는가" 를 명시적 게이트로 판정. 아래 **전부 충족** 시에만 PASS 선언:

- [ ] `verify_commands` 0 errors (**`verify run` 경유**)
- [ ] BLOCKER 0건
- [ ] WARNING 0건 (또는 사용자가 명시적으로 무시 확인)
- [ ] `mx validate --files` 신규·악화 위반 0건
- [ ] `grep -rn "@MX:TODO"` 신규 변경 파일에 미해결 항목 없음 (있으면 후속 티켓 번호가 사유에 명시돼야 통과)

**수렴 안전장치 (발산 방지):**
- 라운드 상한 = 3. 3라운드 내 게이트 미충족이면 무한 반복하지 말고 중단.
- 같은 지적이 2라운드 연속 미해결이거나 수정→새 BLOCKER 발생(발산)이면 → 즉시 중단, Main 이 남은 항목을 사용자에게 보고 후 판단 위임.

$ARGUMENTS
