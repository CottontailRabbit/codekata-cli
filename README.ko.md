# codekata ⚔

**타격감 있는 터미널 코딩 카타.** 코드로 보스를 때려잡는 게임처럼 매일 손가락을 깨웁니다. 정답을 맞히면
화면이 흔들리고 번쩍이며 `CRITICAL`이 떨어지고 보스 HP바가 깎이고, e스포츠 캐스터가 콤보를 외칩니다.
문제는 ChatGPT(Codex CLI)가 만들고, 답은 실제로 **실행해서** 채점하며, 디버거 "킬캠"이 코드를 한 줄씩
다시 보여줍니다.

[English README](README.md)

## 기능

| | |
|---|---|
| **모드** | 랭크전(8스테이지 믹스) · 타자 러시(코드 따라 치기, WPM) · 카타(1~2줄 작성) · 퀴즈(코드 읽기 4지선다) · **로봇SW개발기사 실기 트랙**(Python/C++) |
| **언어** | Python, JavaScript, Rust, C++, Go |
| **타격감** | 화면 흔들림 · 플래시 · 빅텍스트 슬램 · HP 드레인 · 콤보 티어(3/5/7/10/15) · 합성 효과음 · 캐스터/해설 |
| **AI 출제** | ChatGPT(`codex exec` + JSON 스키마), 백그라운드 프리페치(배치당 ~30초). 그동안 내장 문제은행으로 즉시 출제 |
| **채점** | Python/JS는 숨은 테스트까지 실제 실행(하드코딩 불가). 나머지 언어는 정규화/정규식/키워드 → 실패 시 AI VAR 판독 |
| **AI 검증** | AI 카타 모범답안을 실행해 깨진 문제는 버리고, 출력 예측 퀴즈는 실행 결과로 정답을 교정 |
| **디버거** | `sys.settrace` 킬캠 리플레이 — 변수 NEW/CHANGED 강조, 자동재생, 앞뒤 이동 |
| **로깅** | 모든 이벤트(문제/제출/타격/AI 지연/랭킹 업로드)를 `~/.codekata/logs/*.jsonl`에 기록, `codekata log <sid>` 타임라인 |
| **온라인 랭킹** | 랭크전 기록을 공용 GitHub 레포(`gh`) 또는 자체 서버(`codekata serve`)에 업로드 |
| **UI 언어** | 한국어 / English (`--ko`, `--en`, 메뉴에서 `L`, 또는 `codekata config set ui ko`) |

## 준비물

| | 필수? | 용도 |
|---|---|---|
| Python 3.9 이상 | **필수** | 게임 본체 (표준 라이브러리만 사용, pip 의존성 없음) |
| ChatGPT로 로그인한 [Codex CLI](https://github.com/openai/codex) | **강력 권장** | AI 문제 생성, AI VAR 판독. 없으면 오프라인 문제은행(약 80문제)만 출제 |
| `node` | 선택 | JavaScript 답 실행 채점 |
| `g++` | 선택 | C++ 컴파일·실행 채점 |
| `gh` (로그인) | 선택 | GitHub 랭킹 |
| `aplay` / `paplay` / `afplay` | 선택 | 효과음 |

> **왜 Claude가 아니라 ChatGPT인가요?** Claude 구독 로그인은 외부 앱에서 쓸 수 없습니다(API 키 필요).
> Codex CLI는 이미 로그인한 ChatGPT 계정을 그대로 쓸 수 있어서 API 키가 필요 없습니다.

### Codex CLI 설정

```bash
npm install -g @openai/codex     # 또는 brew install codex
codex login                      # "Sign in with ChatGPT" 선택
codekata doctor                  # ✔ codex(ChatGPT) 로그인 이 보이면 준비 완료
```

## 설치

```bash
pipx install git+https://github.com/<OWNER>/<REPO>.git
# 또는 클론해서
git clone https://github.com/<OWNER>/<REPO>.git && cd <REPO> && pipx install .   # (pip install --user . 도 가능)
```

설치 후 `codekata`로 실행합니다. 터미널은 90×32 이상, 256색을 권장합니다.

## 사용법

```bash
codekata                          # 메뉴: 1 랭크전 / 2 러시 / 3 카타 / 4 퀴즈, ←→ 언어, L 한국어/English
codekata play -m mix -l rust      # Rust 랭크전
codekata rush -l python -n 3      # 8스테이지가 아니면 연습(랭킹 미반영)
codekata kata -l js
codekata quiz -l cpp
codekata debug file.py            # 아무 Python 파일이나 킬캠으로
codekata stats                    # 연속 일수, 최고 기록, 언어별 정답률, 추이
codekata log [sid] [--errors|--raw|-f]
codekata rank [-m mix] [-p day|week|all] [-l python]
codekata rank setup               # 온라인 랭킹 연결 (github | http)
codekata auth [login]             # ChatGPT(Codex) 로그인 상태 / 로그인
codekata config [key] [value]     # 예: codekata config set ui en
codekata serve --port 8787 --token SECRET   # 자체 랭킹 서버
codekata doctor
```

전역 옵션(아무 위치): `--ko` `--en` `--debug`(HUD + `~/.codekata/debug.log`) `--no-fx` `--no-sound` `--no-color` `--offline`

### 게임 키

| 스테이지 | 키 |
|---|---|
| 타자 러시 | 코드 그대로 입력(들여쓰기 자동), `Tab` = 공백 4칸, `ESC` 패스 |
| 카타 | `Enter` 제출(3회), `Tab` 힌트(−40%), `ESC` 패스 |
| 퀴즈 | `1`~`4`, 제한 60초, 8초 이내 SPEED KILL |
| 스테이지 후 | `Enter` 다음, `d` 디버거 킬캠, `q` 그만두기 |
| 킬캠 | `→`/`←` 이동, `a` 자동재생, `g`/`G` 처음/끝, `q` 닫기 |

### 점수

콤보 배율 `1 + 0.25 × 콤보`(최대 ×4) · 첫 시도/무오타 크리티컬 · 스피드 보너스 · 보스 K.O. 보너스 ·
FLAWLESS(노미스·노힌트·하트 3개 클리어 +3,000). 등급 SS / S / A / B / C / D.

## 🤖 로봇소프트웨어개발기사 실기 트랙 (`exam` 브랜치)

실기(작업형)의 기본 틀 — **주어진 TXT 입력 파일을 읽어 로봇 공식으로 계산하고, 요구한 형식 그대로 결과 파일에 쓰기** —
를 Python / C++로 연습하는 모드입니다. 이 브랜치로 설치: `pipx install "git+https://github.com/<OWNER>/<REPO>.git@exam"`

```bash
codekata exam                      # 랭크전 5스테이지: 퀴즈 → 카타 → 퀴즈 → 카타 → 실전 작업형(보스)
codekata exam -l cpp               # C++로
codekata exam task                 # 실전 작업형만 (기본 2문제)
codekata exam task -t ik2 -l cpp   # 특정 문제 고정
codekata exam quiz | kata          # 공식·함정 퀴즈 / 공식 한 줄 카타만
codekata exam list                 # 실전 문제 목록
```
메뉴에서는 `5`번(←→로 고른 언어가 python/cpp면 그 언어, 아니면 Python).

| 스테이지 | 내용 | 채점 |
|---|---|---|
| **퀴즈** | 도/라디안, `atan2` 인자 순서, `arange` 끝점, int 나눗셈, `round` 규칙, `-0.000`, signed 바이트, 힙 방향, 격자 `[행][열]`, 인코딩 바이트 수, C++ `fixed`/`setprecision` … | 보기의 정답은 전부 실제 실행 결과로 검증 |
| **카타** | FK/IK·CUBIC·LSPB·BBPB·PID·옥타일 휴리스틱 등 공식 한 줄 | Python은 실행, **C++은 g++로 컴파일·실행**해서 숨은 테스트까지 비교 |
| **실전 작업형** | 작업 폴더에 `input.txt` 생성 → `e`로 에디터(`$CODEKATA_EDITOR`/`$VISUAL`/`$EDITOR`/nano/vim)에서 `solution.py`/`.cpp` 작성 → `r`로 실행·채점 | 레퍼런스 풀이 출력과 **줄 단위 비교**. 값 오류와 형식 오류(자리수·구분자)를 따로 표시, 마지막 자리 ±1은 반올림 경계로 인정 |

실전 작업형 키: `e` 에디터 · `r` 실행/채점 · `h` 힌트(−30%) · `f` 부분점수 제출(50% 이상) · `ESC` 포기(모범답안 표시) ·
문제당 25분. VS Code 등 다른 창에서 파일을 고치고 `r`만 눌러도 됩니다. 작업 폴더는 `~/.codekata/exam/`에 남습니다.
Python 풀이는 끝난 뒤 `d`로 킬캠 디버거를 돌릴 수 있습니다(입력 파일을 읽는 그대로).

실전 문제 12종 (매번 입력이 랜덤 생성): `fk2` 2링크 FK · `ik2` 2링크 IK · `mk2` 자코비안 속도 · `cubic` 3차 궤적 ·
`lspb` 사다리꼴 궤적 · `bbpb` 뱅뱅 궤적 · `dijkstra` · `grid` 8방향 A* · `floyd` · `pid` 제어 시뮬레이션 ·
`can` CAN 프레임 파싱 · `fan` 온도 히스테리시스. 각 문제의 Python·C++ 모범답안이 무작위 입력 40개에서 같은 출력을
내는 것을 확인했습니다.

ChatGPT(Codex)가 붙어 있으면 실기 범위의 퀴즈·카타를 추가로 만들고, C++ 카타는 컴파일해 보고 깨진 문제는 버립니다.
실전 작업형은 레퍼런스 풀이가 있는 문제은행에서만 냅니다.

> **출제 방식 근거 (2026-10 조사)** — Q-net 「2026년도 로봇소프트웨어개발기사 실기시험 안내」(2026년 기사 제3회부터 적용,
> 수험자 개인 PC 지참 불가), 수험자 정리 자료의 공통점: 작업형 약 4~5시간, 시험장 PC(Visual Studio · PyCharm · Excel),
> 언어 C · C++ · Python, 주제는 기구학·궤적·경로 탐색·제어·통신·위치 추정. **시험장 언어·프로그램 환경은 공지 첨부 PDF로
> 직접 확인하세요.** 시험장에 인터넷이 없다고 보고 numpy 없이도 풀 수 있게(`math`만) 레퍼런스를 작성했습니다.

## 온라인 랭킹

랭크전(8스테이지) 기록만 올라갑니다.

* **GitHub** (서버 불필요): `codekata rank setup` → `github` → 공용 레포(예: `you/codekata-ranking`).
  각자 자기 `gh` 로그인으로 `ranking/<login>.json`에 기록하고, 친구는 collaborator로 추가합니다.
* **HTTP**: 어딘가에 `codekata serve --token SECRET`(SQLite, 표준 라이브러리)을 띄우고 `rank setup` → `http`.

업로드에 실패한 기록은 다음 동기화 때 다시 올립니다. 치팅 방지는 없습니다 — 친구끼리 하는 게임입니다.

## 데이터

모두 `~/.codekata/`에 저장됩니다(`CODEKATA_HOME`으로 변경): `config.json`, `history.json`, `logs/`, 효과음.
`CODEKATA_SEED=<n>`을 주면 출제가 고정됩니다(테스트용).
