import argparse
import json
from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from uuid import uuid4

from app.generate_question import generate_questions_from_context
from app.retrieval import get_generation_contexts
from app.review_questions import review_questions


def save_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_question_set(
    document_id: int,
    question_count: int,
    option_count: int,
    max_batches: int,
    output_directory: Path,
) -> dict:
    if not 1 <= question_count <= 100:
        raise ValueError("question_count must be between 1 and 100.")

    if not 3 <= option_count <= 5:
        raise ValueError("option_count must be between 3 and 5.")

    if not 1 <= max_batches <= 100:
        raise ValueError("max_batches must be between 1 and 100.")

    contexts = get_generation_contexts(
        document_id,
        block_count=max_batches,
    )

    accepted_questions = []
    global_sources = {}
    seen_statements = set()
    batch_records = []

    generated_count = 0
    rejected_count = 0
    duplicate_count = 0

    for batch_number, context in enumerate(contexts, start=1):
        remaining = question_count - len(accepted_questions)

        if remaining == 0:
            break

        requested = min(5, remaining)
        prefix = f"batch_{batch_number:03d}"

        save_json(
            output_directory / f"{prefix}_context.json",
            context,
        )

        print(
            f"Batch {batch_number}/{len(contexts)}: "
            f"requesting {requested} questions",
            flush=True,
        )

        batch = generate_questions_from_context(
            context=context,
            question_count=requested,
            option_count=option_count,
            reasoning_effort="none",
        )
        save_json(output_directory / f"{prefix}_generated.json", batch)

        generated_count += len(batch["questions"])
        review = None
        accepted_in_batch = 0

        if batch["questions"]:
            review = review_questions(context, batch)
            save_json(
                output_directory / f"{prefix}_review.json",
                review,
            )

            local_sources = {
                source["source_id"]: source
                for source in batch["sources"]
            }

            for item in review["reviews"]:
                if not item["accepted"]:
                    rejected_count += 1
                    continue

                question = batch["questions"][
                    item["question_number"] - 1
                ]

                normalized_statement = " ".join(
                    question["statement"].casefold().split()
                )

                if normalized_statement in seen_statements:
                    duplicate_count += 1
                    continue

                remapped_ids = []

                for local_id in question["source_ids"]:
                    source = local_sources[local_id]
                    chunk_id = source["chunk_id"]

                    if chunk_id not in global_sources:
                        global_sources[chunk_id] = {
                            **source,
                            "source_id": f"S{len(global_sources) + 1}",
                        }

                    remapped_ids.append(
                        global_sources[chunk_id]["source_id"]
                    )

                accepted_questions.append({
                    **question,
                    "source_ids": list(dict.fromkeys(remapped_ids)),
                })
                seen_statements.add(normalized_statement)
                accepted_in_batch += 1

        batch_records.append({
            "batch_number": batch_number,
            "requested_count": requested,
            "generated_count": len(batch["questions"]),
            "accepted_count": accepted_in_batch,
            "generation_reason": batch["reason"],
            "generation_model": batch["generation_model"],
            "review_model": review["review_model"] if review else None,
            "usage": {
                "generation": batch["usage"],
                "review": review["usage"] if review else None,
            },
        })

        print(
            f"Accepted so far: "
            f"{len(accepted_questions)}/{question_count}",
            flush=True,
        )

    complete = len(accepted_questions) == question_count

    result = {
        "status": "complete" if complete else "partial",
        "document_id": document_id,
        "requested_count": question_count,
        "generated_count": generated_count,
        "accepted_count": len(accepted_questions),
        "rejected_count": rejected_count,
        "duplicate_count": duplicate_count,
        "max_batches": max_batches,
        "available_context_count": len(contexts),
        "processed_batches": len(batch_records),
        "questions": accepted_questions,
        "sources": list(global_sources.values()),
        "reason": (
            None
            if complete
            else (
                "No se alcanzó la cantidad solicitada con los "
                "contextos y el presupuesto de lotes disponibles."
            )
        ),
        "batches": batch_records,
    }

    save_json(output_directory / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate a reviewed question set across contexts."
    )
    parser.add_argument("document_id", type=int)
    parser.add_argument(
        "--question-count",
        type=int,
        choices=range(1, 101),
        default=10,
    )
    parser.add_argument(
        "--option-count",
        type=int,
        choices=[3, 4, 5],
        default=3,
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        choices=range(1, 101),
    )
    args = parser.parse_args()

    if args.document_id <= 0:
        parser.error("document_id must be greater than zero.")

    max_batches = (
        args.max_batches
        if args.max_batches is not None
        else ceil(args.question_count / 5) + 2
    )

    project_root = Path(__file__).resolve().parent.parent
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_{uuid4().hex[:8]}"

    output_directory = (
        project_root / "data" / "question_sets" / run_id
    )
    output_directory.mkdir(parents=True, exist_ok=False)
    print("Output directory:", output_directory, flush=True)

    result = generate_question_set(
        document_id=args.document_id,
        question_count=args.question_count,
        option_count=args.option_count,
        max_batches=max_batches,
        output_directory=output_directory,
    )

    print("Status:", result["status"])
    print("Accepted:", result["accepted_count"])
    print("Rejected:", result["rejected_count"])
    print("Duplicates discarded:", result["duplicate_count"])
    print("Result saved to:", output_directory / "result.json")


if __name__ == "__main__":
    main()