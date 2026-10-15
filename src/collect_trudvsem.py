
"""
Сборщик вакансий с API «Работа России».

Запуск из корня проекта:
python -m src.collect_trudvsem
"""

import json
import time
from pathlib import Path

import requests


API_URL = "https://opendata.trudvsem.ru/api/v1/vacancies"

SEARCH_QUERIES = [
    "NLP",
    "LLM",
    "машинное обучение",
    "обработка естественного языка",
]

# Для первого запуска достаточно небольшой выборки.
VACANCIES_PER_QUERY = 20


def fetch_vacancies(query: str) -> tuple[list[dict], int]:
    """Получает вакансии по поисковому запросу."""

    params = {
        "text": query,
        "limit": VACANCIES_PER_QUERY,
        "offset": 0,
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    # HTTP 200 ещё не гарантирует, что API вернул корректные данные.
    if data.get("status") != "200":
        raise RuntimeError(f"Ошибка API: {data}")

    meta = data.get("meta") or {}
    total = int(meta.get("total", 0))

    results = data.get("results") or {}
    items = results.get("vacancies") or []

    return items, total


def normalize_vacancy(item: dict, query: str) -> dict:
    """Приводит вакансию к общей структуре проекта."""

    vacancy = item.get("vacancy") or {}

    company = vacancy.get("company") or {}
    region = vacancy.get("region") or {}
    requirement = vacancy.get("requirement") or {}

    # Требования иногда представлены строкой, а иногда объектом.
    if isinstance(requirement, dict):
        requirement_text = "; ".join(
            f"{key}: {value}"
            for key, value in requirement.items()
            if value not in (None, "")
        )
    else:
        requirement_text = str(requirement or "")

    return {
        "id": str(vacancy.get("id") or ""),
        "title": vacancy.get("job-name"),
        "company": company.get("name"),
        "area": region.get("name"),
        "url": vacancy.get("vac_url"),
        "published_at": vacancy.get("creation-date"),
        "salary": vacancy.get("salary"),
        "salary_min": vacancy.get("salary_min"),
        "salary_max": vacancy.get("salary_max"),
        "schedule": vacancy.get("schedule"),
        "requirement": requirement_text,
        "description": vacancy.get("duty"),
        "search_query": query,
        "source": "trudvsem.ru",
    }


def main() -> None:
    """Собирает вакансии и сохраняет их в JSON."""

    vacancies_by_id = {}

    for query in SEARCH_QUERIES:
        print(f"\nПоиск: {query}")

        try:
            items, total = fetch_vacancies(query)
        except (requests.RequestException, ValueError, RuntimeError) as error:
            print(f"Не удалось получить данные: {error}")
            continue

        print(f"Всего найдено по запросу: {total}")
        print(f"Получено на этой странице: {len(items)}")

        for item in items:
            normalized = normalize_vacancy(item, query)
            vacancy_id = normalized["id"]

            if vacancy_id:
                # Если вакансия повторилась, сохраняем только одну запись.
                vacancies_by_id[vacancy_id] = normalized

        time.sleep(0.5)

    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "trudvsem_vacancies.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            list(vacancies_by_id.values()),
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nУникальных вакансий: {len(vacancies_by_id)}")
    print(f"Результат сохранён: {output_file}")


if __name__ == "__main__":
    main()
