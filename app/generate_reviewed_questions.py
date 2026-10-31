# generate_reviewed_questions.py

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.generate_question import generate_questions_from_context
from app.retrieval import get_generation_context
from app.review_questions import review_questions


def save_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate and review a question batch."
    )
    parser.add_argument("document_id", type=int)
    parser.add_argument(
        "--question-count",
        type=int,
        choices=range(1, 6),
        default=3,
    )
    parser.add_argument(
        "--option-count",
        type=int,
        choices=[3, 4, 5],
        default=3,
    )
    args = parser.parse_args()

    if args.document_id <= 0:
        parser.error("document_id must be greater than zero.")

    project_root = Path(__file__).resolve().parent.parent
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_{uuid4().hex[:8]}"
    output_directory = (
        project_root / "data" / "generation_runs" / run_id
    )
    output_directory.mkdir(parents=True, exist_ok=False)

    print("Output directory:", output_directory, flush=True)

    context = get_generation_context(args.document_id)
    save_json(output_directory / "context.json", context)

    print("Generating questions...", flush=True)
    batch = generate_questions_from_context(
        context=context,
        question_count=args.question_count,
        option_count=args.option_count,
        reasoning_effort="none",
    )
    save_json(output_directory / "batch.json", batch)

    review = None
    accepted_questions = []
    rejected_questions = []

    if batch["questions"]:
        print("Reviewing questions...", flush=True)
        review = review_questions(context, batch)
        save_json(output_directory / "review.json", review)

        for item in review["reviews"]:
            question = batch["questions"][item["question_number"] - 1]

            if item["accepted"]:
                accepted_questions.append(question)
            else:
                rejected_questions.append({
                    "question_number": item["question_number"],
                    "question": question,
                    "issues": item["issues"],
                })

    accepted_source_ids = {
        source_id
        for question in accepted_questions
        for source_id in question["source_ids"]
    }

    result = {
        "document_id": args.document_id,
        "requested_count": args.question_count,
        "generated_count": len(batch["questions"]),
        "accepted_count": len(accepted_questions),
        "rejected_count": len(rejected_questions),
        "questions": accepted_questions,
        "rejected_questions": rejected_questions,
        "generation_reason": batch["reason"],
        "sources": [
            source
            for source in batch["sources"]
            if source["source_id"] in accepted_source_ids
        ],
        "generation_model": batch["generation_model"],
        "review_model": review["review_model"] if review else None,
        "usage": {
            "generation": batch["usage"],
            "review": review["usage"] if review else None,
        },
    }

    save_json(output_directory / "result.json", result)

    print("Generated:", result["generated_count"])
    print("Accepted:", result["accepted_count"])
    print("Rejected:", result["rejected_count"])
    print("Result saved to:", output_directory / "result.json")


if __name__ == "__main__":
    main()