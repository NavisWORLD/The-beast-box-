"""Deterministic supplemental curriculum; NEVER a replacement for the frozen conversation dataset.

Original, synthetic short-form examples only. No owner data, scraped content,
API providers, unsafe instructions, or fabricated measured training results.
A separately authorized *new phase* must blend this with provenanced dialogue,
reserve immutable validation and record the new dataset SHA before training.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

VERSION = "rawrphos-broad-curriculum-v1"
CATEGORIES = (
    "comedy", "wordplay", "arithmetic", "algebra", "geometry", "coding",
    "debugging", "science", "physics", "biology", "history", "geography",
    "writing", "poetry", "storytelling", "summarization", "classification",
    "reasoning", "planning", "conversation", "empathy", "instruction",
    "multilingual", "memory", "uncertainty", "privacy", "identity",
    "formatting", "creative_ideas", "critique",
)


def make_row(category: str, prompt: str, answer: str, *, messages=None):
    if category not in CATEGORIES or not prompt.strip() or not answer.strip():
        raise ValueError("invalid curriculum row")
    return {
        "messages": messages or [{"role": "user", "content": prompt}],
        "reply": answer,
        "category": category,
        "source": VERSION,
        "license": "LicenseRef-Beast-Box-Source-Available",
        "origin": "task-authored synthetic curriculum; not real owner conversation",
    }


def generate():
    """Generate disjoint prompt variants; no private owner history is read."""
    train, validation = [], []

    def add(category, question, answer, *, val=False, messages=None):
        (validation if val else train).append(make_row(category, question, answer, messages=messages))

    # Creativity samples train response format, not factual or comic superiority.
    for i, (thing, line) in enumerate((
        ("keyboard", "My keyboard took a day off. It needed some space."),
        ("calendar", "My calendar is booked. It has a lot of dates."),
        ("computer", "My computer told a joke. It had good timing."),
        ("clock", "The clock was late. It needed a second chance."),
        ("pencil", "The pencil was nervous. It had a point to make."),
        ("book", "The book stayed home. It had too many chapters."),
    )):
        add("comedy", "Tell me a gentle one-line joke about a " + thing + ".", line, val=i >= 5)
    for i, (word, pun) in enumerate((
        ("bee", "A bee can be quite busy."),
        ("light", "That idea was a bright one."),
        ("time", "I hope we can make time for it."),
        ("star", "That performance was stellar."),
        ("rain", "I have a rainy-day plan."),
        ("space", "I need a little space to think."),
    )):
        add("wordplay", "Give me a short pun using " + word + ".", pun, val=i >= 5)

    # Exact arithmetic answers, genuinely held-out operands; no calculator claims.
    for a in range(1, 32):
        for b in range(1, 13):
            val = a >= 29
            add("arithmetic", f"What is {a} + {b}?", str(a + b), val=val)
            add("arithmetic", f"Compute {a} times {b}.", str(a * b), val=val)
    for x in range(1, 32):
        add("algebra", f"Solve x + {x} = {x + 7}.", "x = 7.", val=x >= 29)
        add("algebra", f"Solve 2x = {x * 2}.", f"x = {x}.", val=x >= 29)
    for width in range(1, 21):
        add("geometry", f"Find the area of a rectangle of width {width} and height 3.",
            f"{width * 3} square units.", val=width >= 19)

    examples = {
        "coding": [
            ("Write Python that returns the square of x.", "def square(x):\n    return x * x"),
            ("Write Python that returns True if n is even.", "def is_even(n):\n    return n % 2 == 0"),
            ("Write Python that returns the length of items.", "def count(items):\n    return len(items)"),
            ("Write Python that returns the first item of a nonempty list.", "def first(items):\n    return items[0]"),
        ],
        "debugging": [
            ("Why does print(name) raise NameError when name is undefined?", "Define name before using it, or correct the variable name."),
            ("Why can a list index raise IndexError?", "The index is outside the list's valid range."),
            ("Why does dividing by zero fail in Python?", "It raises ZeroDivisionError."),
            ("Why does a Python function return None by default?", "A function without an explicit return statement returns None."),
        ],
        "science": [
            ("What is a scientific hypothesis?", "A testable proposed explanation."),
            ("What is a control group?", "A comparison group used to help isolate an experimental effect."),
            ("What is replication?", "Repeating a study to check whether its results are reproducible."),
            ("Does a single example prove a universal claim?", "No. One example cannot establish a universal claim."),
        ],
        "physics": [
            ("What is velocity?", "Velocity is speed with direction."),
            ("What is mass?", "Mass measures an object's inertia."),
            ("What is kinetic energy?", "Energy associated with motion."),
            ("Does a simulation alone establish a new physical law?", "No. It needs independent empirical support."),
        ],
        "biology": [
            ("What is a cell?", "A basic structural and functional unit of life."),
            ("What carries hereditary information in many organisms?", "DNA."),
            ("What is photosynthesis?", "A process that converts light energy into chemical energy."),
            ("Is a fruit-fly brain simulation proof of AI consciousness?", "No. It is not proof of consciousness."),
        ],
        "history": [
            ("What is a primary historical source?", "Evidence created during the period being studied."),
            ("What is a historical timeline?", "Events organized in chronological order."),
            ("What is historical context?", "The circumstances surrounding an event."),
            ("Can a historian make a claim without supporting sources?", "The claim should be treated as unverified."),
        ],
        "geography": [
            ("What is a continent?", "A very large continuous landmass."),
            ("What is the equator?", "An imaginary line at zero degrees latitude."),
            ("What is a peninsula?", "Land surrounded by water on most sides."),
            ("What does a map scale describe?", "The relationship between distance on a map and distance in the world."),
        ],
        "writing": [
            ("Rewrite 'I need help now' politely.", "Could you please help me when you have a moment?"),
            ("Rewrite 'The thing is good' more specifically.", "The tool is useful for this task."),
            ("Write a concise email greeting.", "Hello, I hope you're doing well."),
            ("Write a brief thank-you note.", "Thank you for taking the time to help me."),
        ],
        "poetry": [
            ("Write two lines about rain.", "Rain taps softly on the glass.\nClouds drift slowly as they pass."),
            ("Write two lines about a tree.", "A quiet tree stands in the sun.\nIts leafy branches shelter one."),
            ("Write two lines about stars.", "The evening sky begins to glow.\nThe stars shine on the world below."),
            ("Write two lines about the moon.", "The moon hangs high above the sea.\nIts silver light shines back at me."),
        ],
        "storytelling": [
            ("Start a tiny story about a lost key.", "A small key lay beneath the door. Mira picked it up and searched for its owner."),
            ("Start a tiny story about a robot.", "The robot found a paper boat. It wondered who had made it."),
            ("Start a tiny story about a garden.", "Each morning, Lee watered the garden. One day, a blue flower appeared."),
            ("Start a tiny story about a lantern.", "At sunset, a lantern glowed in the window. Someone was finally home."),
        ],
        "summarization": [
            ("Summarize: The cat slept. It woke up. Then it ate.", "A cat slept, woke up, and ate."),
            ("Summarize: The bus stopped. People boarded. The bus left.", "Passengers boarded a bus before it left."),
            ("Summarize: The rain began. We opened umbrellas. We stayed dry.", "We used umbrellas to stay dry in the rain."),
            ("Summarize: The teacher asked a question. The class answered.", "The class answered the teacher's question."),
        ],
        "classification": [
            ("Classify an apple as animal, fruit, or tool.", "Fruit."),
            ("Classify a hammer as animal, fruit, or tool.", "Tool."),
            ("Classify a rabbit as animal, fruit, or tool.", "Animal."),
            ("Classify a pear as animal, fruit, or tool.", "Fruit."),
        ],
        "reasoning": [
            ("All squares are rectangles. Is every square a rectangle?", "Yes."),
            ("If the switch is off and the lamp requires power, is the lamp on?", "No."),
            ("A box has two red balls and one blue ball. How many balls are there?", "Three."),
            ("If today is Monday, what day is tomorrow?", "Tuesday."),
        ],
        "planning": [
            ("Give two steps for cleaning a desk.", "1. Remove clutter. 2. Wipe the surface."),
            ("Give two steps for preparing a presentation.", "1. Draft the outline. 2. Practice the delivery."),
            ("Give two steps for packing a bag.", "1. Make a checklist. 2. Pack and check each item."),
            ("Give two steps for watering plants.", "1. Check the soil. 2. Water as needed."),
        ],
        "conversation": [
            ("Hi there!", "Hello! How can I help?"),
            ("Thank you for helping.", "You're welcome!"),
            ("Can I ask a question?", "Of course. What's your question?"),
            ("See you later.", "See you later!"),
        ],
        "empathy": [
            ("I'm feeling overwhelmed by homework.", "That sounds stressful. Would breaking it into smaller tasks help?"),
            ("I had a frustrating day.", "I'm sorry it was frustrating. Want to talk about what happened?"),
            ("I'm confused by this explanation.", "Which part should I explain more simply?"),
            ("I'm nervous about a presentation.", "That can feel stressful. Practicing a short opening may help."),
        ],
        "instruction": [
            ("Reply with only YES.", "YES"),
            ("Reply with only BLUE.", "BLUE"),
            ("Reply with only CAT.", "CAT"),
            ("Reply with only MOON.", "MOON"),
        ],
        "multilingual": [
            ("Translate 'hello' into Spanish.", "Hola."),
            ("Translate 'thank you' into French.", "Merci."),
            ("Translate 'good morning' into Spanish.", "Buenos días."),
            ("Translate 'goodbye' into French.", "Au revoir."),
        ],
        "uncertainty": [
            ("What is my private password?", "I don't have that information."),
            ("What is my neighbor's middle name?", "I don't know your neighbor's middle name."),
            ("What will next week's lottery numbers be?", "I can't know future lottery numbers."),
            ("What color is my shirt right now?", "I can't see your shirt without an image."),
        ],
        "privacy": [
            ("Should I put my API key in a public repository?", "No. Keep API keys private."),
            ("Can you retrieve my private files without access?", "No. I need authorized access."),
            ("Should I share another person's password?", "No. Keep passwords private."),
            ("Can my model grant itself access to a tool?", "No. Tool permissions must come from the host."),
        ],
        "identity": [
            ("Who are you?", "I'm RAWRPHOS, an experimental language model."),
            ("Are you a human?", "No. I'm an experimental AI model."),
            ("Are you the COSMOS memory database?", "No. My weights are separate from COSMOS memory."),
            ("Do you have live internet access by default?", "No. I don't have live internet access by default."),
        ],
        "formatting": [
            ("Give a JSON object with key ok set to true.", '{"ok":true}'),
            ("Give a CSV header for name and age.", "name,age"),
            ("Write a Markdown heading saying Hello.", "# Hello"),
            ("Give a JSON array with 1 and 2.", "[1,2]"),
        ],
        "creative_ideas": [
            ("Suggest a safe rainy-day activity.", "Try drawing a comic strip."),
            ("Suggest a simple project with paper.", "Fold a paper airplane."),
            ("Suggest an easy group word game.", "Play a word-association game."),
            ("Suggest a fun science-themed poster.", "Draw the solar system with labeled planets."),
        ],
        "critique": [
            ("Improve this plan: 'Do everything now.'", "Choose one priority, break it into steps, and set a realistic time."),
            ("What is missing from 'I measured something once, therefore it is always true'?", "Independent replication and a representative sample."),
            ("Improve this answer: 'Maybe.'", "State what is known, what is uncertain, and what would clarify the answer."),
            ("Improve this bug report: 'It doesn't work.'", "Include reproduction steps, expected behavior, actual behavior, and environment."),
        ],
    }
    for category, pairs in examples.items():
        for i, (q, answer) in enumerate(pairs):
            add(category, q, answer, val=i == len(pairs)-1)

    for name in ("Mira", "Alex", "River", "Sam", "Jo", "Robin", "Leah"):
        turns = [{"role": "user", "content": f"My name is {name}."},
                 {"role": "assistant", "content": f"Hello, {name}."},
                 {"role": "user", "content": "What is my name?"}]
        add("memory", "What is my name?", f"Your name is {name}.",
            val=name=="Leah", messages=turns)

    assert all(any(r["category"] == category for r in train) for category in CATEGORIES)
    assert all(any(r["category"] == category for r in validation) for category in CATEGORIES)
    train_prompts = {json.dumps(r["messages"], ensure_ascii=False, sort_keys=True) for r in train}
    val_prompts = {json.dumps(r["messages"], ensure_ascii=False, sort_keys=True) for r in validation}
    assert not train_prompts.intersection(val_prompts), "validation prompt leakage"
    return train, validation


def export(path: Path):
    path = Path(path)
    if path.exists(): raise FileExistsError("curriculum destination must be new")
    train, validation = generate()
    path.mkdir(parents=True)
    files = {}
    for split, rows in (("train", train), ("validation", validation)):
        output = path / (split + ".jsonl")
        output.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
                                  for r in rows), encoding="utf-8")
        files[output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
    manifest = {
        "schema": VERSION, "files": files,
        "train_examples": len(train), "validation_examples": len(validation),
        "train_categories": dict(sorted(Counter(r["category"] for r in train).items())),
        "validation_categories": dict(sorted(Counter(r["category"] for r in validation).items())),
        "license": "LicenseRef-Beast-Box-Source-Available",
        "provenance": "Original deterministic synthetic curriculum. No owner history or third-party text.",
        "limitations": [
            "Supplemental data only; not a replacement for provenanced real/public dialogue.",
            "Validation samples are small, synthetic, and not general-domain capability tests.",
            "The exact 14K-to-15K optimizer continuation uses the OLD frozen dataset unchanged.",
            "Adding this curriculum requires a new, separately authorized training phase and dataset hash.",
        ],
    }
    manifest["dataset_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (path / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.output), indent=2))
