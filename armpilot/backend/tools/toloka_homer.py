"""
Toloka HomER dataset integration.

Loads the HomER (Home Egocentric Robotics) dataset from Hugging Face
and finds relevant egocentric video demonstrations for the current task.
This enriches the reasoning agent with real-world manipulation knowledge.

Dataset: https://huggingface.co/datasets/toloka/HomER
"""

import asyncio
from typing import Optional


# Cache the dataset in memory after first load
_homer_cache: Optional[list[dict]] = None


async def load_homer_dataset() -> list[dict]:
    """Load HomER dataset from HuggingFace. Cached after first call."""
    global _homer_cache
    if _homer_cache is not None:
        return _homer_cache

    def _load():
        try:
            from datasets import load_dataset
            ds = load_dataset("toloka/HomER", split="train")
            records = []
            for row in ds:
                records.append({
                    "video_id": row["video_id"],
                    "video_url": row["video_url"],
                    "task_category": row["task_category"],
                    "scenario": row["scenario"],
                    "description": row["description"],
                    "duration_sec": row["duration_sec"],
                })
            return records
        except Exception as e:
            print(f"[HomER] Failed to load dataset: {e}")
            return _get_fallback_data()

    _homer_cache = await asyncio.to_thread(_load)
    return _homer_cache


def _get_fallback_data() -> list[dict]:
    """Fallback data if HuggingFace is unreachable."""
    return [
        {
            "video_id": 1,
            "video_url": "",
            "task_category": "Kitchen & Food Handling",
            "scenario": "Pick up a mug from counter",
            "description": "Person picks up a ceramic mug from the kitchen counter using one hand, demonstrating careful grip on the handle.",
            "duration_sec": 45.0,
        },
        {
            "video_id": 2,
            "video_url": "",
            "task_category": "Object Manipulation & Organization",
            "scenario": "Sort items by size",
            "description": "Person sorts various household items by size on a table, moving smallest to largest from left to right.",
            "duration_sec": 60.0,
        },
        {
            "video_id": 3,
            "video_url": "",
            "task_category": "Fragile & Deformable",
            "scenario": "Handle glass carefully",
            "description": "Person carefully picks up a glass cup, demonstrating cautious grip and slow movements to avoid breakage.",
            "duration_sec": 35.0,
        },
        {
            "video_id": 4,
            "video_url": "",
            "task_category": "Cleaning & Household Tasks",
            "scenario": "Wipe table surface",
            "description": "Person wipes a table surface using a cloth, demonstrating sweeping arm motions.",
            "duration_sec": 40.0,
        },
        {
            "video_id": 5,
            "video_url": "",
            "task_category": "Object Handoff",
            "scenario": "Hand object to person",
            "description": "Person picks up an object and hands it to another person, demonstrating safe handoff technique.",
            "duration_sec": 30.0,
        },
    ]


async def find_relevant_demos(
    command: str,
    objects: list[str],
    max_results: int = 3,
) -> list[dict]:
    """
    Find HomER videos relevant to the current task.
    Uses keyword matching on task_category, scenario, and description.
    """
    dataset = await load_homer_dataset()

    # Build search terms from command and objects
    search_terms = command.lower().split()
    for obj in objects:
        search_terms.extend(obj.lower().split())

    # Score each video by keyword overlap
    scored = []
    for record in dataset:
        text = f"{record['task_category']} {record['scenario']} {record['description']}".lower()
        score = sum(1 for term in search_terms if term in text)
        if score > 0:
            scored.append((score, record))

    # Sort by score descending, return top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:max_results]]


async def get_homer_context(command: str, objects: list[str]) -> str:
    """
    Get HomER context string to inject into the reasoning agent prompt.
    Returns a formatted string describing relevant egocentric demonstrations.
    """
    demos = await find_relevant_demos(command, objects)
    if not demos:
        return ""

    lines = ["[Toloka HomER — Egocentric Demonstrations]"]
    for d in demos:
        lines.append(
            f"- [{d['task_category']}] {d['scenario']}: {d['description']} "
            f"(video_id={d['video_id']}, {d['duration_sec']:.0f}s)"
        )
    return "\n".join(lines)
