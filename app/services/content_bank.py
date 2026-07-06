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
    return ensure_bank("quiz.json", _gen.generate_quizzes, 1000)


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