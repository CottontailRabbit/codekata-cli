"""e스포츠 중계 톤 캐스터/해설 대사 (ko / en)."""
import random

from . import i18n

LINES_KO = {
    "start": [
        "자, {boss} 등장! 오늘의 손가락 컨디션 확인 들어갑니다!",
        "경기 시작합니다! 상대는 {boss}! 키보드 예열 완료!",
        "{boss}가 코드베이스를 점령했습니다! 막아야 합니다!",
        "관중석 술렁입니다! {boss} 대 도전자, 지금 시작!",
    ],
    "next_boss": [
        "끝이 아닙니다! 2페이즈! {boss} 난입!!",
        "쉴 틈이 없어요! 다음 상대 {boss}!",
    ],
    "hit": [
        "들어갑니다! 깔끔한 일격! {dmg} 데미지!",
        "정타! {boss} 휘청거립니다!",
        "꽂혔습니다! 이게 기본기죠!",
        "좋아요, 그대로 밀어붙입니다!",
        "교과서 같은 한 방! {dmg}!",
    ],
    "crit": [
        "크리티컬!!! 첫 타에 급소를 꿰뚫습니다!",
        "이게 들어가네요!! 원샷 원킬 각!",
        "CRITICAL! {dmg}! 보스 HP바가 쭉쭉 빠집니다!",
        "망설임이 없어요! 한 번에 정답, 크리티컬!",
    ],
    "speed": [
        "빠르다! {sec}초 만에 결판!",
        "번개 같은 손놀림! {sec}초!",
        "문제 읽긴 했나요?! {sec}초 컷!",
    ],
    "perfect": [
        "퍼펙트! 오타 하나 없이 관통!",
        "무결점 타이핑! 이게 프로의 손입니다!",
        "PERFECT! 키보드가 박수를 칩니다!",
    ],
    "combo3": ["{n}콤보! 손이 풀리기 시작합니다!", "{n}연속! 흐름 탔어요!"],
    "combo5": ["{n}연타아아! 리듬 탔어요, 리듬!", "{n}콤보! 상대가 반응을 못 합니다!"],
    "combo7": ["{n}콤보!!! 이건 막을 수가 없어요!", "{n}콤보! 키보드에서 불꽃이 튑니다!"],
    "combo10": ["{n}콤보?! 사람입니까 컴파일러입니까!", "두 자릿수 콤보 진입! {n}!! 경기장이 뒤집힙니다!"],
    "combo15": ["{n}콤보… 해설진 할 말을 잃었습니다. 전설입니다!", "{n}콤보! 오늘 이 경기, 하이라이트 확정!"],
    "miss": [
        "아아~ 빗나갑니다!",
        "막혔어요! 다시 노려봐야 합니다!",
        "헛스윙! {boss}가 비웃습니다!",
        "아쉽다! 각도가 살짝 틀어졌어요!",
    ],
    "combo_break": [
        "콤보 브레이크!! {n}콤보가 산산조각!",
        "아아아—! {n}콤보가 끊겼습니다!",
        "{n}콤보 여기서 멈춥니다! 뼈아픈 실수!",
    ],
    "heart": [
        "피격! 남은 하트 {hearts}개!",
        "치명상! 라이프 하나가 날아갑니다!",
        "{boss}의 반격! 하트가 깨집니다!",
    ],
    "last_heart": ["벼랑 끝입니다! 하트 하나! 한 번만 더 맞으면 끝!", "숨 막히는 상황! 마지막 하트!"],
    "boss_low": ["{boss} 체력 바닥! 마무리 일격만 남았습니다!", "{boss} 비틀거립니다! 지금이에요 지금!"],
    "ko": [
        "K.O.!!! {boss} 격파! 코드베이스에 평화가 찾아옵니다!",
        "끝났습니다아아! {boss} 완전히 녹아내립니다!",
        "{boss} 다운!!! 카운트 필요 없습니다!",
    ],
    "flawless": ["FLAWLESS! 노데미지 클리어! 오늘 이분 손 보험 들어야 합니다!"],
    "game_over": ["쓰러집니다… GAME OVER. 하지만 내일의 손가락은 더 강해집니다!",
                  "여기까지! 하트 소진! 리매치를 기다리겠습니다!"],
    "escape": ["{boss}가 도망칩니다! 아깝다, 다음엔 반드시!", "타임업! {boss} 간신히 살아남습니다!"],
    "streak": ["{n}타 연속 무오타! 손끝에서 레이저가!", "{n}타 스트릭! 이 리듬 끊지 마세요!",
               "{n}타 노미스! 기계식 키보드가 노래합니다!"],
    "streak_break": ["오타! {n}타 스트릭 종료!", "아! 손가락이 꼬였어요! {n}타에서 끊깁니다!"],
    "hint": ["힌트 사용! 자존심 대신 점수를 냅니다 (-{cost})", "힌트 오픈! 전략적 판단이죠."],
    "skip": ["패스! 전략적 후퇴입니다.", "넘깁니다! 다음 라운드에서 만회해야죠!"],
    "reveal": ["3연속 실패… 정답 공개합니다. 이건 꼭 기억해 두세요!"],
    "timeout": ["타임 오버!! 시계가 먼저 끝났습니다!"],
    "record": ["신기록!!! 개인 최고 {score}점 경신!"],
    "var": ["VAR 판독 들어갑니다… 비디오 판독 중!", "판정이 애매합니다! VAR 갑니다!"],
    "var_ok": ["VAR 결과… 정답 인정!! 골이에요 골!"],
    "var_no": ["VAR 결과… 노골! 판정 번복 없습니다!"],
}

LINES_EN = {
    "start": [
        "{boss} enters the arena! Fingers warmed up? Let's find out!",
        "And we are LIVE! Tonight's opponent: {boss}! Keyboards ready!",
        "{boss} has taken over the codebase! Somebody has to stop it!",
        "The crowd is on its feet! {boss} versus the challenger — GO!",
    ],
    "next_boss": [
        "It's not over! Phase two! {boss} crashes the party!",
        "No time to breathe! Next up: {boss}!",
    ],
    "hit": [
        "That one lands! Clean strike for {dmg}!",
        "Direct hit! {boss} is staggering!",
        "Right on target! Fundamentals, folks!",
        "Good, keep the pressure on!",
        "Textbook! {dmg} damage!",
    ],
    "crit": [
        "CRITICAL!!! First try, straight through the weak spot!",
        "Did you see that?! One shot, one kill!",
        "CRITICAL! {dmg}! The boss HP bar is melting!",
        "No hesitation at all! First attempt, critical hit!",
    ],
    "speed": [
        "So fast! Decided in {sec} seconds!",
        "Lightning hands! {sec} seconds!",
        "Did you even read the question?! {sec}-second clear!",
    ],
    "perfect": [
        "PERFECT! Not a single typo!",
        "Flawless typing! Those are pro hands!",
        "PERFECT! The keyboard is applauding!",
    ],
    "combo3": ["{n} combo! The hands are loosening up!", "{n} in a row! We're in the flow!"],
    "combo5": ["{n}-HIT COMBO! Feel that rhythm!", "{n} combo! The opponent can't even react!"],
    "combo7": ["{n} COMBO!!! This is unstoppable!", "{n} combo! Sparks flying off the keyboard!"],
    "combo10": ["{n} combo?! Human or compiler?!", "Double-digit combo! {n}!! The arena explodes!"],
    "combo15": ["{n} combo... the commentary desk is speechless. LEGENDARY!", "{n} combo! Instant highlight reel!"],
    "miss": [
        "Ohh~ just wide!",
        "Blocked! Gotta line it up again!",
        "Whiff! {boss} is laughing!",
        "So close! The angle was just a bit off!",
    ],
    "combo_break": [
        "COMBO BREAKER!! The {n} combo shatters!",
        "Nooo—! The {n} combo is gone!",
        "The {n} combo ends here! That one hurts!",
    ],
    "heart": [
        "Hit taken! {hearts} hearts left!",
        "Big damage! A life slips away!",
        "{boss} counters! A heart breaks!",
    ],
    "last_heart": ["On the edge! One heart left — one more hit and it's over!", "Breathless! Last heart!"],
    "boss_low": ["{boss} is almost out! Just the finisher left!", "{boss} is wobbling! Now, NOW!"],
    "ko": [
        "K.O.!!! {boss} is down! Peace returns to the codebase!",
        "IT'S OVER! {boss} completely melts away!",
        "{boss} DOWN!!! No count needed!",
    ],
    "flawless": ["FLAWLESS! A no-damage clear! Somebody insure those hands!"],
    "game_over": ["Down they go... GAME OVER. But tomorrow's fingers will be stronger!",
                  "That's it! Out of hearts! We'll be waiting for the rematch!"],
    "escape": ["{boss} escapes! So close — next time for sure!", "Time! {boss} barely survives!"],
    "streak": ["{n} keys without a typo! Lasers from the fingertips!", "{n}-key streak! Don't break that rhythm!",
               "{n} no-miss! The mechanical keyboard is singing!"],
    "streak_break": ["Typo! The {n}-key streak ends!", "Ah! Fingers tangled! Broken at {n}!"],
    "hint": ["Hint used! Points over pride (-{cost})", "Hint open! A tactical decision."],
    "skip": ["Pass! A strategic retreat.", "Skipped! Gotta make it up next round!"],
    "reveal": ["Three misses... here's the answer. Remember this one!"],
    "timeout": ["TIME OVER!! The clock got there first!"],
    "record": ["NEW RECORD!!! Personal best {score} smashed!"],
    "var": ["Going to VAR... video review in progress!", "Too close to call! VAR check!"],
    "var_ok": ["VAR decision... ANSWER STANDS!! GOAL!"],
    "var_no": ["VAR decision... no goal! The call stands!"],
}

_last = {}


def say(event, **kw):
    lines = LINES_EN if i18n.UI == "en" else LINES_KO
    pool = lines.get(event) or [""]
    choices = [x for x in pool if x != _last.get(event)] or pool
    line = random.choice(choices)
    _last[event] = line
    kw.setdefault("dmg", "")
    try:
        return line.format(**kw)
    except (KeyError, IndexError):
        return line


def combo_event(n):
    for k in (15, 10, 7, 5, 3):
        if n >= k and (n == k or (k >= 10 and n % 5 == 0)):
            return f"combo{k}"
    return None


def combo_color(n):
    from . import fx
    if n >= 15:
        return fx.RAINBOW[n % len(fx.RAINBOW)]
    if n >= 10:
        return fx.MAGENTA
    if n >= 7:
        return fx.RED
    if n >= 5:
        return fx.ORANGE
    if n >= 3:
        return fx.YELLOW
    return fx.GREY
