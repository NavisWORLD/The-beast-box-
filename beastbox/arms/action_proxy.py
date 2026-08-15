from __future__ import annotations

from copy import deepcopy
from typing import Any

# Native llama.cpp GBNF keeps the compact Beast Arms action syntactically valid
# without injecting a large JSON-schema prompt into QC67's 128-token context.
# Keep the wire form whitespace-free and finite: the model still chooses the
# tool and arguments, but every syntactically permitted action has a bounded
# completion path inside the model's small native active window.
COMPACT_ACTION_GRAMMAR = r'''
root ::= "{\"t\":" tool ",\"a\":" object0 "}"
tool ::= "\"l\"" | "\"r\"" | "\"w\"" | "\"x\"" | "\"q\"" | "\"s\"" | "\"p\"" | "\"o\"" | "\"k\"" | "\"h\"" | "\"d\"" | "\"g\"" | "\"a\"" | "\"e\"" | "\"n\"" | "\"m\"" | "\"c\"" | "\"f\""
object0 ::= "{}" | "{" member0 ("," member0){0,1} "}"
member0 ::= key ":" value0
object1 ::= "{}" | "{" member1 ("," member1){0,1} "}"
member1 ::= key ":" value1
key ::= "\"path\"" | "\"max_bytes\"" | "\"content\"" | "\"find\"" | "\"replace\"" | "\"count\"" | "\"query\"" | "\"limit\"" | "\"argv\"" | "\"pid\"" | "\"url\"" | "\"method\"" | "\"headers\"" | "\"body\"" | "\"host\"" | "\"port\"" | "\"action\"" | "\"key\"" | "\"value\"" | "\"note\"" | "\"message\""
value0 ::= scalar | array0 | object1
value1 ::= scalar | array1
array0 ::= "[]" | "[" value1 ("," value1){0,2} "]"
array1 ::= "[]" | "[" scalar ("," scalar){0,2} "]"
scalar ::= string | number | "true" | "false" | "null"
string ::= "\"" char{0,24} "\""
char ::= [^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" hex hex hex hex)
number ::= "-"? int frac? exp?
int ::= "0" | [1-9] [0-9]{0,5}
frac ::= "." [0-9]{1,4}
exp ::= [eE] [+-]? [0-9]{1,3}
hex ::= [0-9a-fA-F]
'''.strip()


def rewrite_chat_request(payload: dict[str, Any], *, max_tokens: int = 96) -> dict[str, Any]:
    """Return a copy of an OpenAI-compatible request constrained by GBNF.

    The model still chooses every tool alias and argument. This function only
    changes the wire-format constraint and output budget; containment and tool
    authorization are enforced separately by Beast Arms.
    """
    out = deepcopy(payload)
    out.pop("response_format", None)
    out["grammar"] = COMPACT_ACTION_GRAMMAR
    out["max_tokens"] = int(max_tokens)
    return out
