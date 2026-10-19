"""오프라인 문제은행. AI(ChatGPT) 프리페치가 준비되기 전/오프라인일 때 즉시 출제된다."""
import hashlib

from . import i18n
from .bank_en import EN

LANG_LABEL = {"python": "Python", "js": "JavaScript", "ts": "TypeScript", "rust": "Rust", "cpp": "C++",
              "go": "Go", "java": "Java", "kotlin": "Kotlin", "swift": "Swift", "zig": "Zig"}
LANG_COLOR = {"python": 33, "js": 226, "ts": 39, "rust": 208, "cpp": 129, "go": 51, "java": 166,
              "kotlin": 135, "swift": 202, "zig": 214}


def R(lang, title, code, explain=""):
    return {"kind": "rush", "lang": lang, "title": title, "code": code, "explain": explain}


def K(lang, title, desc, answer, setup="", tests=(), hint="", accept=(), explain=""):
    return {"kind": "kata", "lang": lang, "title": title, "desc": desc, "setup": setup, "tests": list(tests),
            "answer": answer, "hint": hint, "accept": list(accept), "explain": explain}


def Q(lang, title, code, question, options, correct, explain):
    return {"kind": "quiz", "lang": lang, "title": title, "code": code, "question": question,
            "options": list(options), "correct": correct, "explain": explain}


RUSH = [
    R("python", "딕셔너리 컴프리헨션", "squares = {n: n * n for n in range(10) if n % 2}"),
    R("python", "with 파일 읽기", 'with open(path, encoding="utf-8") as f:\n    lines = [l.rstrip() for l in f]'),
    R("python", "clamp", "def clamp(x, lo, hi):\n    return max(lo, min(x, hi))"),
    R("python", "리더보드 출력",
      'for i, (name, score) in enumerate(sorted(board.items(), key=lambda kv: -kv[1])):\n'
      '    print(f"{i + 1:>2}. {name:<10} {score:,}")'),
    R("python", "dataclass", "@dataclass(frozen=True)\nclass Hit:\n    damage: int\n    crit: bool = False"),
    R("python", "async fetch", "async def fetch(session, url):\n    async with session.get(url) as r:\n        return await r.json()"),
    R("python", "페어 묶기", "pairs = list(zip(xs[::2], xs[1::2]))"),
    R("python", "첫 매치", "first = next((x for x in items if x.ok), None)"),
    R("python", "Counter", "top3 = Counter(w.lower() for w in text.split()).most_common(3)"),
    R("js", "reduce 합계", "const sum = arr.reduce((a, b) => a + b, 0);"),
    R("js", "중복 제거", "const ids = [...new Set(items.map(i => i.id))];"),
    R("js", "clamp 화살표", "export const clamp = (x, lo, hi) => Math.min(Math.max(x, lo), hi);"),
    R("js", "이벤트 바인딩", 'document.querySelectorAll("button").forEach(b => b.addEventListener("click", hit));'),
    R("js", "async/await", "const res = await fetch(url);\nif (!res.ok) throw new Error(`HTTP ${res.status}`);\nconst data = await res.json();"),
    R("js", "구조분해", "const { name, score = 0, ...rest } = player;"),
    R("rust", "필터 합계", "let total: i32 = v.iter().filter(|&&x| x > 0).sum();"),
    R("rust", "clamp fn", "fn clamp(x: f64, lo: f64, hi: f64) -> f64 {\n    x.max(lo).min(hi)\n}"),
    R("rust", "match", 'match cmd.as_str() {\n    "hit" => combo += 1,\n    _ => combo = 0,\n}'),
    R("rust", "split collect", "let words: Vec<&str> = line.split_whitespace().collect();"),
    R("rust", "derive struct", "#[derive(Debug, Clone, PartialEq)]\nstruct Hit { dmg: u32, crit: bool }"),
    R("rust", "if let", "if let Some(boss) = bosses.iter_mut().find(|b| b.hp > 0) {\n    boss.hp -= dmg;\n}"),
    R("cpp", "람다 정렬", "std::sort(v.begin(), v.end(), [](int a, int b) { return a > b; });"),
    R("cpp", "find_if", "auto it = std::find_if(v.begin(), v.end(), [&](const auto& x) { return x.id == id; });"),
    R("cpp", "구조적 바인딩", 'for (const auto& [name, score] : board) {\n    std::cout << name << ": " << score << \'\\n\';\n}'),
    R("cpp", "make_unique", 'auto boss = std::make_unique<Boss>("Segfault", 9000);'),
    R("cpp", "템플릿 clamp", "template <typename T>\nT clamp(T x, T lo, T hi) { return std::max(lo, std::min(x, hi)); }"),
    R("cpp", "lock_guard", "std::lock_guard<std::mutex> lock(mtx);\nqueue.push(std::move(job));"),
    R("go", "range 루프", "for i, v := range nums {\n    sum += v * i\n}"),
    R("go", "에러 래핑", 'if err != nil {\n    return fmt.Errorf("hit failed: %w", err)\n}'),
    R("go", "채널", "ch := make(chan int, 10)\ngo func() { ch <- 42 }()"),
]

KATA = [
    K("python", "중복 제거 + 정렬", "nums의 중복을 제거하고 오름차순 정렬한 리스트를 만드세요.",
      "sorted(set(nums))", setup="nums = [3, 1, 4, 1, 5, 9, 2, 6]", tests=["nums = [5, 5, 2]"],
      hint="set, sorted", explain="`set`으로 중복 증발, `sorted`가 리스트로 돌려줍니다. 두 동작 한 줄 콤보!"),
    K("python", "길이 필터 + 대문자", "words에서 길이 3 이상인 단어만 대문자로 바꾼 리스트를 만드세요.",
      "[w.upper() for w in words if len(w) >= 3]", setup='words = ["kata", "code", "py", "rust"]',
      tests=['words = ["ab", "abc"]'], hint="리스트 컴프리헨션 + if",
      explain="컴프리헨션의 `if`는 필터, 앞쪽 표현식은 변환. 필터-맵을 한 줄에 겁니다!"),
    K("python", "최빈 문자", "s에서 가장 많이 등장하는 문자 하나를 구하세요.",
      "Counter(s).most_common(1)[0][0]", setup='from collections import Counter\ns = "hello world"',
      tests=['from collections import Counter\ns = "banana"'], hint="Counter.most_common",
      explain="`Counter`가 빈도를 세고 `most_common(1)`이 1등만 뽑아줍니다. `[0][0]`으로 문자만 추출!"),
    K("python", "두 리스트 → 딕셔너리", "b를 키, a를 값으로 하는 딕셔너리를 만드세요.",
      "dict(zip(b, a))", setup='a = [1, 2, 3]\nb = ["x", "y", "z"]', tests=['a = [9]\nb = ["k"]'],
      hint="zip", explain="`zip`이 짝을 맞춰 튜플을 만들고 `dict`가 그대로 흡수합니다. 정석 콤비네이션!"),
    K("python", "행렬 전치", "matrix를 전치(transpose)한 리스트의 리스트를 만드세요.",
      "[list(r) for r in zip(*matrix)]", setup="matrix = [[1, 2, 3], [4, 5, 6]]",
      tests=["matrix = [[1, 2], [3, 4], [5, 6]]"], hint="zip(*...)",
      explain="`*matrix`로 행들을 펼쳐 `zip`에 넣으면 열 단위로 묶입니다. 언패킹 + zip, 전치의 필살기!"),
    K("python", "회문 판정", "s가 회문(앞뒤가 같은 문자열)이면 True, 아니면 False가 되게 하세요.",
      "s == s[::-1]", setup='s = "racecar"', tests=['s = "kata"', 's = "abba"'], hint="슬라이싱 [::-1]",
      explain="`[::-1]`은 역방향 슬라이스. 원본과 비교 한 번이면 끝! (숨은 테스트가 있어 True 하드코딩은 막힙니다)"),
    K("python", "짝수 제곱합", "1부터 n까지 짝수들의 제곱의 합을 구하세요.",
      "sum(x * x for x in range(2, n + 1, 2))", setup="n = 10", tests=["n = 5", "n = 1"],
      hint="range(start, stop, step)", explain="`range`의 step=2로 짝수만 순회, 제너레이터 식을 `sum`에 바로 투입!"),
    K("python", "확장자 추출", "path에서 마지막 점 뒤의 확장자를 구하세요.",
      'path.rsplit(".", 1)[-1]', setup='path = "/home/user/project/main.py"', tests=['path = "a/b.tar.gz"'],
      hint="rsplit(sep, maxsplit)", explain="`rsplit`은 오른쪽부터 자릅니다. maxsplit=1이라 `tar.gz`도 `gz`만 깔끔하게!"),
    K("python", "값 기준 정렬 키", "data를 값 기준 내림차순으로 정렬한 키 리스트를 만드세요.",
      "sorted(data, key=data.get, reverse=True)", setup='data = {"b": 2, "a": 3, "c": 1}',
      tests=['data = {"x": 1, "y": 5}'], hint="key=data.get",
      explain="`key=data.get`으로 각 키의 값을 정렬 기준으로! 람다 없이 메서드 참조로 한 방!"),
    K("python", "숫자만 합산", "s에 들어 있는 숫자 문자들을 정수로 바꿔 모두 더하세요.",
      "sum(int(c) for c in s if c.isdigit())", setup='s = "a1b2c3"', tests=['s = "x9y9"'],
      hint="str.isdigit", explain="`isdigit`으로 숫자만 걸러 `int`로 변환해 `sum`. 필터-변환-집계 3연타!"),
    K("python", "청크 나누기", "xs를 3개씩 끊은 리스트의 리스트를 만드세요. (마지막은 남는 만큼)",
      "[xs[i:i + 3] for i in range(0, len(xs), 3)]", setup="xs = [1, 2, 3, 4, 5, 6, 7]",
      tests=["xs = [1, 2]"], hint="range(0, len, 3) + 슬라이싱",
      explain="3씩 점프하는 인덱스로 슬라이스! 슬라이싱은 범위를 넘어도 에러가 없어 꼬리도 안전합니다."),
    K("python", "단어 세기", "text에서 단어 'the'가 몇 번 나오는지 세세요. (부분 문자열 말고 단어 단위)",
      'text.split().count("the")', setup='text = "the quick brown the lazy the"',
      tests=['text = "the other theme the"'], hint="split + count",
      explain="`text.count('the')`는 'other' 안의 the까지 셉니다! `split()`으로 단어 단위로 끊어야 정확합니다."),
    K("js", "최댓값", "nums의 최댓값을 구하세요.", "Math.max(...nums)", setup="const nums = [5, 3, 8, 1];",
      tests=["const nums = [-2, -9];"], hint="스프레드 ...",
      explain="`Math.max`는 배열이 아니라 인자 목록을 받습니다. 스프레드로 펼쳐 넣는 게 핵심!"),
    K("js", "문자열 뒤집기", "s를 뒤집은 문자열을 만드세요.", '[...s].reverse().join("")', setup='const s = "hello";',
      tests=['const s = "abc";'], hint="스프레드 → reverse → join",
      explain="문자열엔 `reverse`가 없으니 배열로 펼쳐 뒤집고 다시 `join`. 3단 콤보!"),
    K("js", "짝수만 두 배", "arr에서 짝수만 골라 각각 2배로 만든 배열을 만드세요.",
      "arr.filter(x => x % 2 === 0).map(x => x * 2)", setup="const arr = [1, 2, 3, 4];",
      tests=["const arr = [5, 6];"], hint="filter → map",
      explain="`filter`로 거르고 `map`으로 변환. 메서드 체이닝의 정석입니다!"),
    K("js", "조건 이름 추출", "users 중 age가 25 이상인 사람의 name 배열을 만드세요.",
      "users.filter(u => u.age >= 25).map(u => u.name)",
      setup='const users = [{name: "a", age: 30}, {name: "b", age: 20}];',
      tests=['const users = [{name: "z", age: 25}];'], hint="filter + map",
      explain="객체 배열도 똑같이 `filter → map`. `>=` 경계값 25를 놓치지 마세요!"),
    K("js", "빈도 객체", "words의 단어별 등장 횟수 객체를 만드세요. 예: {a: 2, bb: 1}",
      "words.reduce((m, w) => (m[w] = (m[w] || 0) + 1, m), {})", setup='const words = ["a", "bb", "a"];',
      tests=['const words = ["x"];'], hint="reduce + 초기값 {}",
      explain="`reduce`의 누산기를 객체로! `(m[w] || 0) + 1`이 없는 키를 0으로 시작시켜 줍니다."),
    K("js", "kebab → camel", "str(케밥 케이스)을 camelCase로 바꾸세요.",
      'str.replace(/-(\\w)/g, (_, ch) => ch.toUpperCase())', setup='const str = "code-kata-cli";',
      tests=['const str = "a-b";'], hint="replace + 정규식 g + 콜백",
      explain="`/-(\\w)/g`가 하이픈 뒤 글자를 캡처하고 콜백이 대문자로 치환. 정규식 콜백 한 방!"),
    K("rust", "범위 합계", "1부터 10까지(포함)의 합을 구하는 표현식을 쓰세요. (i32)",
      "(1..=10).sum::<i32>()", hint="..= 와 sum",
      accept=[r"re:\(1\.\.=10\)\.sum(::<i32>)?\(\)", r"re:\(1\.\.11\)\.sum(::<i32>)?\(\)"],
      explain="`..=`는 끝 포함 범위. `sum`은 반환 타입을 알아야 해서 터보피시 `::<i32>`가 필요할 때가 많아요!"),
    K("rust", "짝수 Vec", "v: Vec<i32>에서 짝수만 모은 새 Vec<i32>를 만드세요.",
      "v.iter().filter(|x| *x % 2 == 0).cloned().collect::<Vec<i32>>()", hint="iter → filter → collect",
      accept=["kw:filter collect %2==0 iter|into_iter"],
      explain="`iter()`는 참조를 내주니 `cloned()`로 값 복사 후 `collect`. `into_iter()`면 소유권째 가져갑니다!"),
    K("rust", "Option 기본값", "opt: Option<i32>가 None이면 0, 아니면 안의 값을 얻으세요.",
      "opt.unwrap_or(0)", hint="unwrap_or",
      accept=["opt.unwrap_or_default()", "kw:matchopt Some None=>0"],
      explain="`unwrap_or(0)`은 패닉 없는 안전한 언래핑! i32는 Default가 0이라 `unwrap_or_default()`도 정답."),
    K("rust", "공백 분리", "s: &str을 공백 기준으로 나눠 Vec<&str>로 모으세요.",
      "s.split_whitespace().collect::<Vec<&str>>()", hint="split_whitespace",
      accept=["kw:split_whitespace|split(' ')|split(\" \") collect"],
      explain="`split_whitespace`는 연속 공백·탭·개행까지 알아서 처리. `split(' ')`보다 튼튼합니다!"),
    K("rust", "문자열 길이", "s: String의 바이트 길이를 구하세요.", "s.len()", hint="len",
      explain="`len()`은 '글자 수'가 아니라 바이트 수! 한글은 글자당 3바이트라 `chars().count()`와 다릅니다."),
    K("cpp", "벡터 정렬", "std::vector<int> v를 오름차순 정렬하세요.", "std::sort(v.begin(), v.end());",
      hint="<algorithm>", accept=[r"re:(std::)?sort\(v\.begin\(\),v\.end\(\)\)", r"re:(std::)?ranges::sort\(v\)"],
      explain="`std::sort`는 반복자 쌍을 받습니다. C++20이면 `std::ranges::sort(v)`로 더 짧게!"),
    K("cpp", "벡터 합", "std::vector<int> v의 합을 구하는 표현식을 쓰세요.",
      "std::accumulate(v.begin(), v.end(), 0)", hint="<numeric>",
      accept=["kw:accumulate( v.begin() v.end() ,0)"],
      explain="`accumulate`의 세 번째 인자가 초기값이자 결과 타입! `0.0`을 넣으면 double로 누적됩니다."),
    K("cpp", "unique_ptr 생성", "값 42를 가진 int의 unique_ptr p를 만드세요.",
      "auto p = std::make_unique<int>(42);", hint="make_unique", accept=["kw:make_unique<int>(42) p"],
      explain="`make_unique`는 예외 안전하고 `new`를 숨겨줍니다. 스마트 포인터 생성의 정석!"),
    K("cpp", "개수 세기", "std::vector<int> v에서 3의 개수를 구하세요.", "std::count(v.begin(), v.end(), 3)",
      hint="std::count", accept=["kw:count( v.begin() v.end() ,3)"],
      explain="`std::count`는 값과 같은 원소 수를 셉니다. 조건으로 세려면 `count_if`!"),
    K("cpp", "대문자 변환", "std::string s를 제자리에서 대문자로 바꾸세요.",
      "std::transform(s.begin(), s.end(), s.begin(), ::toupper);", hint="std::transform + toupper",
      accept=["kw:transform toupper s.begin()"],
      explain="출력 반복자로 `s.begin()`을 다시 주면 제자리 변환! 엄밀히는 `unsigned char` 람다가 더 안전합니다."),
]

QUIZ = [
    Q("python", "가변 기본값의 함정",
      "def add(x, acc=[]):\n    acc.append(x)\n    return acc\n\nadd(1)\nprint(add(2))",
      "출력은?", ["[1, 2]", "[2]", "[1]", "TypeError"], 0,
      "기본값 `[]`은 함수 정의 때 딱 한 번 만들어집니다! 호출마다 같은 리스트가 재사용돼 [1, 2]. 해결은 `acc=None`!"),
    Q("python", "클로저 늦은 바인딩",
      "fs = [lambda: i for i in range(3)]\nprint([f() for f in fs])",
      "출력은?", ["[0, 1, 2]", "[2, 2, 2]", "[0, 0, 0]", "NameError"], 1,
      "람다는 `i`의 값이 아니라 변수를 붙잡습니다. 호출 시점의 i는 2! `lambda i=i: i`로 값 고정해야 합니다."),
    Q("python", "리스트 곱셈 별칭",
      "grid = [[0] * 3] * 2\ngrid[0][0] = 1\nprint(grid)",
      "출력은?", ["[[1, 0, 0], [0, 0, 0]]", "[[1, 0, 0], [1, 0, 0]]", "[[1, 1, 1], [0, 0, 0]]", "TypeError"], 1,
      "바깥 `* 2`는 같은 내부 리스트 참조를 두 번 복사! 한 줄 고치면 두 줄이 같이 바뀝니다. `[[0]*3 for _ in range(2)]`!"),
    Q("python", "슬라이싱 연타",
      's = "codekata"\nprint(s[-4:], s[::3])',
      "출력은?", ["kata cek", "kata cet", "akat cet", "kata cdk"], 1,
      "`s[-4:]`는 뒤에서 4글자 kata, `s[::3]`은 인덱스 0,3,6 → c, e, t. 스텝 슬라이스 정확히 읽기!"),
    Q("python", "dict.get 기본값",
      'd = {"a": 1, "b": 2}\nd["a"] = 3\nd["c"] = d.get("z", 0) + d["b"]\nprint(list(d.items()))',
      "출력은?", ["[('a', 3), ('b', 2), ('c', 2)]", "[('b', 2), ('a', 3), ('c', 2)]", "KeyError: 'z'",
                 "[('a', 3), ('b', 2), ('c', 0)]"], 0,
      "기존 키 갱신은 순서를 안 바꾸고, `get`은 없는 키에 기본값 0을 줍니다. 0 + 2 = 2!"),
    Q("python", "제너레이터 소진",
      "g = (x * x for x in range(4))\nprint(sum(g), sum(g))",
      "출력은?", ["14 14", "14 0", "0 14", "TypeError"], 1,
      "제너레이터는 일회용! 첫 `sum`이 0+1+4+9=14를 다 먹어버려 두 번째는 빈손, 0입니다."),
    Q("python", "음수 나눗셈과 반올림",
      "print(-7 // 2, -7 % 2, round(2.5))",
      "출력은?", ["-3 -1 3", "-4 1 2", "-4 1 3", "-3 1 2"], 1,
      "`//`는 바닥 나눗셈이라 -4, 나머지는 부호가 제수를 따라 1. `round`는 은행가 반올림이라 2.5 → 2!"),
    Q("python", "두 배씩 커지는 루프",
      "def f(n):\n    i = 1\n    while i < n:\n        i *= 2\n    return i",
      "시간복잡도는?", ["O(n)", "O(log n)", "O(n log n)", "O(1)"], 1,
      "i가 매번 두 배! n에 닿기까지 log₂n번이면 끝납니다. 곱셈 증가는 로그의 신호!"),
    Q("python", "finally의 출력 순서",
      'def f():\n    try:\n        return "try"\n    finally:\n        print("finally", end=" ")\n\nprint(f())',
      "출력은?", ["try finally", "finally try", "try", "finally"], 1,
      "`return` 값이 정해진 뒤 함수가 빠져나가기 직전에 `finally`가 실행됩니다. 그래서 finally가 먼저 찍힙니다!"),
    Q("python", "전역 변수 갱신",
      "count = 0\ndef inc():\n    count += 1\n    return count\n\nprint(inc())",
      "실행 결과는?", ["1", "0", "UnboundLocalError", "NameError"], 2,
      "함수 안에서 대입하면 `count`는 지역 변수로 간주! 읽기 전에 += 하니 UnboundLocalError. `global count` 필요!"),
    Q("js", "sort의 기본 비교",
      "console.log([1, 2, 10].sort());",
      "출력은?", ["[ 1, 2, 10 ]", "[ 1, 10, 2 ]", "[ 10, 2, 1 ]", "TypeError"], 1,
      "기본 `sort`는 문자열 비교! '10' < '2'라서 [1, 10, 2]. 숫자는 `(a, b) => a - b`를 넘기세요!"),
    Q("js", "var와 setTimeout",
      "for (var i = 0; i < 3; i++) {\n  setTimeout(() => console.log(i), 0);\n}",
      "출력은? (줄바꿈 생략)", ["0 1 2", "3 3 3", "undefined undefined undefined", "2 2 2"], 1,
      "`var`는 함수 스코프라 i가 하나뿐! 콜백이 돌 땐 루프가 끝나 i=3. `let`이면 반복마다 새 바인딩이라 0 1 2."),
    Q("js", "부동소수와 NaN",
      "console.log(0.1 + 0.2 === 0.3, typeof NaN);",
      "출력은?", ["true number", "false number", "false NaN", "true undefined"], 1,
      "0.1+0.2는 0.30000000000000004! 그리고 NaN도 엄연한 number 타입입니다. JS 2대 함정!"),
    Q("js", "+ 연산자 형변환",
      "console.log([] + {}, [1, 2] + [3]);",
      "출력은?", ["[object Object] 1,23", "{} [1,2,3]", "0 1,2,3", "TypeError"], 0,
      "`+`는 객체를 문자열로 바꿉니다. []→'', {}→'[object Object]', [1,2]→'1,2'에 '3'이 붙어 '1,23'!"),
    Q("rust", "소유권 이동",
      'fn main() {\n    let s = String::from("hi");\n    let t = s;\n    println!("{}", s);\n}',
      "결과는?", ["hi 출력", "컴파일 에러: 이동된 값 사용", "빈 문자열 출력", "런타임 panic"], 1,
      "`let t = s;`에서 String 소유권이 t로 이동! s는 더 이상 유효하지 않아 컴파일러가 막습니다 (E0382)."),
    Q("rust", "wrapping vs checked",
      'fn main() {\n    let x: u8 = 255;\n    let y = x.wrapping_add(1);\n    let z = x.checked_add(1);\n    println!("{} {:?}", y, z);\n}',
      "출력은?", ["0 None", "256 Some(256)", "panic", "0 Some(0)"], 0,
      "`wrapping_add`는 255+1을 0으로 감고, `checked_add`는 오버플로면 None! 의도를 타입으로 표현하는 Rust 방식."),
    Q("rust", "섀도잉과 스코프",
      'fn main() {\n    let x = 5;\n    let x = x * 2;\n    {\n        let x = x + 1;\n        print!("{} ", x);\n    }\n    println!("{}", x);\n}',
      "출력은?", ["11 11", "11 10", "6 5", "컴파일 에러"], 1,
      "섀도잉은 새 변수를 만드는 것! 블록 안의 x=11은 블록이 끝나면 사라지고 바깥 x=10이 돌아옵니다."),
    Q("rust", "게으른 이터레이터",
      'fn main() {\n    let v = vec![1, 2, 3];\n    v.iter().map(|x| println!("{}", x));\n    println!("done");\n}',
      "출력은?", ["1 2 3 done", "done", "컴파일 에러", "아무것도 출력 안 됨"], 1,
      "이터레이터 어댑터는 게으릅니다! 소비(`for`, `collect`)하지 않으면 map 클로저는 실행조차 안 돼요 (경고만)."),
    Q("cpp", "정수 나눗셈",
      "#include <iostream>\nint main() {\n    int a = 7, b = 2;\n    double r = a / b;\n    std::cout << r << \"\\n\";\n}",
      "출력은?", ["3.5", "3", "4", "컴파일 에러"], 1,
      "`a / b`는 int끼리 먼저 계산돼 3이 된 뒤 double로 변환! `static_cast<double>(a) / b` 해야 3.5."),
    Q("cpp", "값 복사 vs 참조",
      "#include <iostream>\n#include <vector>\nint main() {\n    std::vector<int> v{1, 2, 3};\n    for (auto x : v) x *= 2;\n    for (auto& y : v) y += 1;\n    std::cout << v[0] << v[1] << v[2];\n}",
      "출력은?", ["357", "234", "246", "123"], 1,
      "`auto x`는 복사본이라 원본은 그대로! `auto& y`만 원본을 수정해서 각각 +1 → 234."),
    Q("cpp", "signed/unsigned 비교",
      '#include <iostream>\nint main() {\n    unsigned int u = 1;\n    int i = -1;\n    std::cout << (i < u ? "less" : "greater");\n}',
      "출력은?", ["less", "greater", "컴파일 에러", "정의되지 않은 동작"], 1,
      "비교 시 -1이 unsigned로 변환돼 4294967295가 됩니다! 그래서 greater. -Wsign-compare 경고를 켜세요."),
    Q("cpp", "배열의 포인터 붕괴",
      '#include <iostream>\nvoid f(int arr[10]) { std::cout << sizeof(arr) << " "; }\nint main() {\n    int a[10];\n    std::cout << sizeof(a) << " ";\n    f(a);\n}',
      "출력은? (64비트, int=4바이트)", ["40 40", "40 8", "10 10", "8 8"], 1,
      "함수 매개변수의 `int arr[10]`은 사실 `int*`! 배열이 포인터로 붕괴해 sizeof가 8. `std::array`나 `span`을 쓰세요."),
]


def localize(p):
    """문제 사본을 현재 UI 언어로. ("ko", "en") 튜플 필드와 bank_en 번역을 적용한다."""
    p = dict(p)
    for k in ("title", "desc", "hint", "question", "explain", "topic", "fmt"):
        if k in p:
            p[k] = i18n.pick(p[k])
    if "options" in p:
        p["options"] = [i18n.pick(o) for o in p["options"]]
    if i18n.UI == "en" and p.get("source") == "bank":
        tr = EN.get(p.get("title_ko") or p["title"], {})
        for k, v in tr.items():
            if k == "options":
                p["options"] = [v.get(o, o) for o in p["options"]]
            else:
                p[k] = v
    return p


def pid(p):
    key = f"{p['kind']}|{p['lang']}|{p['title']}"
    return hashlib.sha1(key.encode()).hexdigest()[:10]


ALL = RUSH + KATA + QUIZ
for _p in ALL:
    _p["id"] = pid(_p)
    _p["source"] = "bank"
    _p["title_ko"] = _p["title"]
