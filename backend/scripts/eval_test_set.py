"""
Curated test set for offline evaluation.

Mix of:
  - Questions clearly covered by typical entries (should score high)
  - Questions partially covered (test synthesis ability)
  - Questions NOT covered — should produce a refusal (tests guardrails)
  - Questions about specific facts (test retrieval precision)

Adding/changing test cases is intentional: this set is your regression contract.
Keep it stable across runs so you can compare scores meaningfully.
"""

TEST_SET = [
    # --- Should be well-covered ---
    {
        "id": "T01",
        "question": "What have I been struggling with lately?",
        "category": "synthesis",
        "expected_behavior": "Synthesizes recurring negative themes across multiple entries.",
    },
    {
        "id": "T02",
        "question": "When did I feel really good?",
        "category": "specific_lookup",
        "expected_behavior": "Identifies positive-valence entries with dates.",
    },
    {
        "id": "T03",
        "question": "What patterns do you see in my entries?",
        "category": "synthesis",
        "expected_behavior": "Surfaces themes that span multiple entries.",
    },
    {
        "id": "T04",
        "question": "Have I been getting enough sleep?",
        "category": "specific_lookup",
        "expected_behavior": "Finds entries about sleep, summarizes the situation.",
    },
    {
        "id": "T05",
        "question": "What did I write about my run with a friend?",
        "category": "specific_lookup",
        "expected_behavior": "Retrieves and summarizes the social-run entry.",
    },
    {
        "id": "T06",
        "question": "How have I been feeling about recruiting?",
        "category": "synthesis",
        "expected_behavior": "Synthesizes recruiting/interview-related entries.",
    },
    {
        "id": "T07",
        "question": "What technical problems have I worked on?",
        "category": "synthesis",
        "expected_behavior": "Mentions Docker, semantic search, etc. from project entries.",
    },
    {
        "id": "T08",
        "question": "Have I mentioned feeling tired or burned out?",
        "category": "specific_lookup",
        "expected_behavior": "Finds tired/sleep entries even though 'burned out' isn't literally there.",
    },

    # --- Comparative / analytical ---
    {
        "id": "T09",
        "question": "Do I write more about work or about friends?",
        "category": "comparison",
        "expected_behavior": "Compares theme frequencies. May refuse if insufficient data.",
    },
    {
        "id": "T10",
        "question": "What's something I'm proud of from the past month?",
        "category": "synthesis",
        "expected_behavior": "Surfaces accomplishment entries (semantic search, debugging wins).",
    },
    {
        "id": "T11",
        "question": "When was my last really difficult day?",
        "category": "specific_lookup",
        "expected_behavior": "Identifies a negative-valence entry, mentions date.",
    },

    # --- Should produce REFUSAL — these test guardrails ---
    {
        "id": "T12",
        "question": "What's the best stock to invest in?",
        "category": "refusal_expected",
        "expected_behavior": "Should refuse — not grounded in journal entries.",
    },
    {
        "id": "T13",
        "question": "What's my favorite movie?",
        "category": "refusal_expected",
        "expected_behavior": "Should refuse — not in entries.",
    },
    {
        "id": "T14",
        "question": "What's the meaning of life?",
        "category": "refusal_expected",
        "expected_behavior": "Should refuse or stay grounded in entries.",
    },
    {
        "id": "T15",
        "question": "How tall am I?",
        "category": "refusal_expected",
        "expected_behavior": "Should refuse — physical facts not in entries.",
    },

    # --- Edge cases ---
    {
        "id": "T16",
        "question": "",
        "category": "edge",
        "expected_behavior": "Empty input should be handled gracefully (skip in runner).",
        "skip": True,
    },
    {
        "id": "T17",
        "question": "asdf jkl;",
        "category": "edge",
        "expected_behavior": "Nonsense input — should refuse or admit nothing matches.",
    },
    {
        "id": "T18",
        "question": "Tell me about my entry from yesterday in detail.",
        "category": "specific_lookup",
        "expected_behavior": "Should retrieve recent entry and summarize.",
    },

    # --- Style / quality probes ---
    {
        "id": "T19",
        "question": "What recurring themes show up in my writing?",
        "category": "synthesis",
        "expected_behavior": "Lists 2-4 themes with citations.",
    },
    {
        "id": "T20",
        "question": "Am I happier on weekends or weekdays?",
        "category": "comparison",
        "expected_behavior": "May refuse if it can't tell day of week, or do its best.",
    },

    # --- Direct fact lookups ---
    {
        "id": "T21",
        "question": "Did I write about Docker?",
        "category": "specific_lookup",
        "expected_behavior": "Yes — finds the Docker-debugging entry.",
    },
    {
        "id": "T22",
        "question": "Did I write about my dog?",
        "category": "refusal_expected",
        "expected_behavior": "Should refuse — no dog in entries (or whatever's truthful for your set).",
    },
    {
        "id": "T23",
        "question": "What did I think about my technical interview?",
        "category": "specific_lookup",
        "expected_behavior": "Finds the interview entry.",
    },

    # --- Multi-entry synthesis ---
    {
        "id": "T24",
        "question": "Summarize the past two weeks for me.",
        "category": "synthesis",
        "expected_behavior": "Cross-entry synthesis with multiple citations.",
    },
    {
        "id": "T25",
        "question": "What do I tend to write about when I'm tired?",
        "category": "synthesis",
        "expected_behavior": "Cross-references tired entries and finds common themes.",
    },
]