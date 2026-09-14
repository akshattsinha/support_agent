import sys
from pathlib import Path

PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)

from app.reply import (
    retrieve_reply_context,
)


# ============================================================
# EVALUATION CASES
# ============================================================

CASES = [
    {
        "name": "Password Reset",
        "text": (
            "I forgot my password and "
            "cannot log into my account."
        ),
        "expected_source": "account_login.md",
    },
    {
        "name": "Billing",
        "text": (
            "I was charged twice for "
            "the same subscription."
        ),
        "expected_source": "billing.md",
    },
    {
        "name": "Security",
        "text": (
            "Someone accessed my account "
            "without my permission."
        ),
        "expected_source": "security.md",
    },
    {
        "name": "Assessment",
        "text": (
            "My browser crashed while I "
            "was taking an assessment."
        ),
        "expected_source": "assessment_issues.md",
    },
]


# ============================================================
# RUN
# ============================================================

def main():

    passed = 0

    total = len(
        CASES
    )

    print()
    print(
        "=" * 70
    )

    print(
        "AI SUPPORT SENTINEL"
    )

    print(
        "RAG RETRIEVAL EVALUATION"
    )

    print(
        "=" * 70
    )

    for case in CASES:

        results = retrieve_reply_context(
            case["text"],
            limit=4,
        )

        sources = [
            item["name"]
            for item in results
        ]

        expected = (
            case["expected_source"]
        )

        success = (
            expected in sources
        )

        if success:

            passed += 1

            status = "PASS"

        else:

            status = "FAIL"

        print()
        print(
            f"[{status}] "
            f"{case['name']}"
        )

        print(
            f"Expected: {expected}"
        )

        print(
            f"Retrieved: {sources}"
        )

    print()
    print(
        "=" * 70
    )

    accuracy = (
        passed / total
        if total
        else 0
    )

    print(
        f"Retrieval accuracy: "
        f"{accuracy:.1%}"
    )

    print(
        f"Passed: {passed}/{total}"
    )

    print(
        "=" * 70
    )

    if passed != total:

        raise SystemExit(1)


if __name__ == "__main__":

    main()