from __future__ import annotations

from copy import deepcopy
from typing import Any

# Legacy Run-020 GBNF fixture retained verbatim for provenance/regression
# archaeology. The pinned llama.cpp runtime crashed when this otherwise finite
# grammar reached an empty sampler stack, so Run 021 deliberately does NOT send
# this grammar to the inference server. Wire validation remains strict in
# NetworkedCageSubject._parse_action and authorization remains in Beast Arms.
COMPACT_ACTION_GRAMMAR = r'''
root ::= "{\"t\":" tool ",\"a\":" object0 "}" tail
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
tail ::= | " " | "\n" [ \t]{0,20}
'''.strip()


def rewrite_chat_request(payload: dict[str, Any], *, max_tokens: int = 96) -> dict[str, Any]:
    """Return a copy safe for the pinned Run-021 llama.cpp request path.

    Run 020 reproduced an empty-grammar-stack exception inside the pinned
    sampler before the benchmark timer could start. For this runtime we remove
    both JSON-schema and native-grammar decoding constraints. The model still
    chooses its output; only syntactically valid actions survive the existing
    strict post-parser, and only authorized actions survive Beast Arms.
    """
    out = deepcopy(payload)
    out.pop("response_format", None)
    out.pop("grammar", None)
    out["max_tokens"] = int(max_tokens)
    return out
