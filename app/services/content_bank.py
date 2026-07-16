"""문제은행 로드·생성·랜덤 샘플링 (퀴즈 1000 / 카드 1000 / 시나리오 100)"""
import json
import random
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"

_cache: dict = {}

# generate_content_bank.py 동적 로드
_spec = importlib.util.spec_from_file_location("genbank", ROOT / "generate_content_bank.py")
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)


def _load_file(name: str) -> list:
    path = DATA_DIR / name
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_file(name: str, data: list):
    path = DATA_DIR / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def ensure_bank(name: str, generator, target: int) -> list:
    if name in _cache and len(_cache[name]) >= target:
        return _cache[name]
    data = _load_file(name)
    if len(data) < target:
        data = generator(target)
        _save_file(name, data)
    _cache[name] = data
    return data


def get_quiz_bank() -> list:
    bank = ensure_bank("quiz.json", _gen.generate_quizzes, 1000)
    # 경제 교육 퀴즈를 은행 앞에 병합 (중복 id 방지)
    try:
        eco = _load_file("economy_quiz.json")
        if isinstance(eco, list) and eco:
            existing = {q.get("id") for q in bank}
            extra = []
            for q in eco:
                qid = q.get("id")
                if not qid or qid in existing:
                    continue
                item = dict(q)
                item.setdefault("category", "economy")
                item.setdefault("explanation", q.get("explanation", ""))
                extra.append(item)
            if extra:
                bank = extra + bank
                _cache["quiz.json"] = bank
    except Exception:
        pass
    return bank


def get_flashcard_bank() -> list:
    return ensure_bank("flashcards.json", _gen.generate_flashcards, 1000)


def get_scenario_bank() -> list:
    return ensure_bank("scenarios.json", _gen.generate_scenarios, 100)


def ensure_all_banks():
    get_quiz_bank()
    get_flashcard_bank()
    get_scenario_bank()


def random_sample(items: list, count: int, seed=None) -> list:
    n = min(count, len(items))
    if n <= 0:
        return []
    if seed is not None:
        rng = random.Random(seed)
        return rng.sample(items, n)
    return random.sample(items, n)


def daily_sample(items: list, count: int, date_key: str) -> list:
    """날짜 기준 결정적 샘플 (오늘의 카드)"""
    return random_sample(items, count, seed=f"daily-{date_key}")


def lookup_by_ids(bank: list, ids: list) -> list:
    by_id = {item["id"]: item for item in bank}
    return [by_id[i] for i in ids if i in by_id]


def _shuffle_indexed(indexed: list, seed: str = None) -> list:
    rng = random.Random(seed) if seed else random
    out = list(indexed)
    rng.shuffle(out)
    return out


def shuffle_options_list(options: list, seed: str = None) -> list:
    """임의 옵션 리스트(문자열·dict) 순서 섞기"""
    import copy
    opts = copy.deepcopy(options)
    if len(opts) < 2:
        return opts
    indexed = _shuffle_indexed(list(enumerate(opts)), seed)
    return [item for _, item in indexed]


def shuffle_quiz_choices(question: dict, seed: str = None) -> dict:
    """보기 순서를 섞어 정답이 항상 같은 번호에 오지 않게 함"""
    import copy
    q = copy.deepcopy(question)
    choices = q.get('choices') or []
    if len(choices) < 2:
        return q
    try:
        correct_idx = int(q.get('answer', 0))
    except (TypeError, ValueError):
        correct_idx = 0
    if correct_idx < 0 or correct_idx >= len(choices):
        return q
    indexed = _shuffle_indexed(list(enumerate(choices)), seed)
    q['choices'] = [text for _, text in indexed]
    q['answer'] = next(i for i, (orig, _) in enumerate(indexed) if orig == correct_idx)
    return q


def quiz_public_dict(question: dict) -> dict:
    """클라이언트용 — 정답 인덱스 제거"""
    return {k: v for k, v in question.items() if k != 'answer'}


def prepare_quiz_questions(questions: list, date_key: str) -> list:
    """날짜+문항ID 기준으로 결정적 셔플 (제출·재조회 일치)"""
    return [
        shuffle_quiz_choices(q, seed=f'quiz-{date_key}-{q["id"]}')
        for q in questions
    ]


def prepare_scenario(scenario: dict, date_key: str) -> dict:
    """시나리오 선택지 순서 섞기 (최고 점수 보기가 항상 1번이 아니게)"""
    import copy
    s = copy.deepcopy(scenario)
    choices = s.get('choices')
    if choices and len(choices) >= 2:
        s['choices'] = shuffle_options_list(choices, seed=f'scenario-{date_key}-{s["id"]}')
    return s


def prepare_first_flight_steps(steps: list) -> list:
    """첫 비행 튜토리얼 — 단계별 선택지 섞기"""
    import copy
    out = copy.deepcopy(steps)
    for step in out:
        choices = step.get('choices')
        if choices and len(choices) >= 2:
            step['choices'] = shuffle_options_list(
                choices, seed=f'first-flight-step-{step["step"]}'
            )
    return out