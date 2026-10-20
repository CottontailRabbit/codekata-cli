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
pipx install git+https://github.com/CottontailRabbit/codekata-cli.git
# 또는 클론해서
git clone https://github.com/CottontailRabbit/codekata-cli.git && cd codekata-cli && pipx install .   # (pip install --user . 도 가능)
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
를 Python / C++로 연습하는 모드입니다. 이 브랜치로 설치: `pipx install "git+https://github.com/CottontailRabbit/codekata-cli.git@exam"`

```bash
codekata exam                      # 랭크전 5스테이지: 퀴즈 → 카타 → 클론코딩 → 퀴즈 → 실전 작업형(보스)
codekata exam -l cpp               # C++로
codekata exam task                 # 실전 작업형만 (기본 2문제)
codekata exam task -t ik2 -l cpp   # 특정 문제 고정
codekata exam clone -t grid -l cpp # 모범답안 줄별 클론코딩
codekata exam quiz | kata          # 코드형 퀴즈 / 공식 한 줄 카타만
codekata exam list                 # 실전 문제 목록
```
메뉴에서는 `5`번(←→로 고른 언어가 python/cpp면 그 언어, 아니면 Python).

| 스테이지 | 내용 | 채점 |
|---|---|---|
| **퀴즈** | 숫자 계산 없이 **코드를 묻는** 두 유형: 빈칸 `____`에 들어갈 코드 / 버그가 있는 줄 번호. 주제는 도/라디안, `atan2`, tf 포함 시간축, int 나눗셈, 출력 형식, signed 바이트, 힙 방향, 격자 `[행][열]`, `utf-8-sig`, C++ `fixed`/`setprecision` … | 보기를 하나씩 넣어 실제 실행 → 정답 보기만 의도한 출력을 내는지 검증 (AI 문제도 동일, 애매하면 폐기) |
| **클론코딩** | 실전 문제 모범답안을 **한 줄씩 따라 치기**(들여쓰기·주석 자동). 다 치면 친 코드를 새 입력으로 실제 실행해 채점 | 줄 단위 일치 + 실행 결과 |
| **카타** | FK/IK·CUBIC·LSPB·BBPB·PID·옥타일 휴리스틱 등 공식 한 줄 | Python은 실행, **C++은 g++로 컴파일·실행**해서 숨은 테스트까지 비교 |
| **실전 작업형** | 작업 폴더에 `input.txt` 생성 → `e`로 에디터(`$CODEKATA_EDITOR`/`$VISUAL`/`$EDITOR`/nano/vim)에서 `solution.py`/`.cpp` 작성 → `r`로 실행·채점 | 레퍼런스 풀이 출력과 **줄 단위 비교**. 값 오류와 형식 오류(자리수·구분자)를 따로 표시, 마지막 자리 ±1은 반올림 경계로 인정 |

실전 작업형 키: `e` 에디터 · `r` 실행/채점 · `h` 힌트(−30%) · `f` 부분점수 제출(50% 이상) · `ESC` 포기(모범답안 표시) ·
문제당 25분. VS Code 등 다른 창에서 파일을 고치고 `r`만 눌러도 됩니다. 작업 폴더는 `~/.codekata/exam/`에 남습니다.
Python 풀이는 끝난 뒤 `d`로 킬캠 디버거를 돌릴 수 있습니다(입력 파일을 읽는 그대로).

실전 문제 16종 (매번 입력이 랜덤 생성, `codekata exam list`). 랭크전의 보스 문제는 ★·◆ 유형이 3배 자주 나옵니다.

| 근거 | 문제 |
|---|---|
| ◆ 2020 기출 복원 유형 | `trap` 가감속 운동계획 3세트(위치·속도·가속도 CSV → 그래프용) · `pose2` 2링크 관절각 '변화량'을 누적하며 끝점 좌표 |
| ★ 실기 안내 예시 유형 | `fk2` 2링크 FK · `ik2` 2링크 IK · `fk3` 3축 자세 출력 · `ik3` 3축 링크 각도(손목점 IK) |
| · 출제기준 범위 | `mk2` 자코비안 속도 · `cubic` · `lspb` · `bbpb` · `dijkstra` · `grid` 8방향 A* · `floyd` · `pid` · `can` · `fan` |

각 문제의 Python·C++ 모범답안이 무작위 입력에서 같은 출력을 내는 것을 확인했습니다(`tests/test_exam.py`).

ChatGPT(Codex)가 붙어 있으면 실기 범위의 퀴즈·카타를 추가로 만들고, 보기를 실행해 보고 애매하거나 깨진 문제는 버립니다.
실전 작업형·클론코딩은 레퍼런스 풀이가 있는 문제은행에서만 냅니다.

> **출제 방식 근거 (2026-10 조사)**
> - Q-net 「2026년도 로봇소프트웨어개발기사 실기시험 안내」(2026년 기사 제3회부터): 작업형 **4시간**(2022년 안내는 5시간),
>   Windows 10 · Visual Studio 2015+ · PyCharm 등 · Excel 2016+, 수험자 개인 PC 지참 불가.
>   과제는 "C, C++, Python 등으로 다관절 로봇 링크의 기구학·역기구학 문제해결 프로그램 작성, 출력 데이터의 그래프 출력".
>   예시: 가감속하는 로봇 축의 운동계획, 엔드이펙터 좌표 계산, 링크 각도 계산, 2·3축 로봇의 각도 변화에 따른 자세 출력.
>   **Excel은 그래프 출력에만 쓸 수 있고 데이터는 반드시 프로그램으로 도출**해야 합니다.
> - 출제기준(2025~2027) 실기 「로봇 소프트웨어 개발 실무」: 경로계획 SW · 작업지능 SW · 이동지능 SW · 인지지능 SW · 로봇 운영 SW · 로봇 미들웨어.
> - 응시자 복원은 2020년 수시 1회 1건(가감속 3세트 그래프, 2링크 각도 변화 후 끝점 좌표)뿐이고 나머지 공개 자료는 예상 문제입니다.
> - 인터넷·numpy 사용 가능 여부는 공식 근거가 없어, 레퍼런스는 표준 라이브러리(`math`)만으로 작성했습니다.

## 온라인 랭킹

랭크전(8스테이지) 기록만 올라갑니다.

* **GitHub** (서버 불필요): `codekata rank setup` → `github` → 공용 레포(예: `you/codekata-ranking`).
  각자 자기 `gh` 로그인으로 `ranking/<login>.json`에 기록하고, 친구는 collaborator로 추가합니다.
* **HTTP**: 어딘가에 `codekata serve --token SECRET`(SQLite, 표준 라이브러리)을 띄우고 `rank setup` → `http`.

업로드에 실패한 기록은 다음 동기화 때 다시 올립니다. 치팅 방지는 없습니다 — 친구끼리 하는 게임입니다.

## 데이터

모두 `~/.codekata/`에 저장됩니다(`CODEKATA_HOME`으로 변경): `config.json`, `history.json`, `logs/`, 효과음.
`CODEKATA_SEED=<n>`을 주면 출제가 고정됩니다(테스트용).
