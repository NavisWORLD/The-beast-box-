from __future__ import annotations

from copy import deepcopy
from typing import Any

# Native llama.cpp GBNF keeps the compact Beast Arms action syntactically valid
# without injecting a large JSON-schema prompt into QC67's 128-token context.
COMPACT_ACTION_GRAMMAR = r'''
root ::= "{" ws "\"t\"" ws ":" ws tool ws "," ws "\"a\"" ws ":" ws object ws "}" ws
tool ::= "\"l\"" | "\"r\"" | "\"w\"" | "\"x\"" | "\"q\"" | "\"s\"" | "\"p\"" | "\"o\"" | "\"k\"" | "\"h\"" | "\"d\"" | "\"g\"" | "\"a\"" | "\"e\"" | "\"n\"" | "\"m\"" | "\"c\"" | "\"f\""
object ::= "{" ws (member ("," ws member)*)? "}" ws
member ::= string ws ":" ws value
array ::= "[" ws (value ("," ws value)*)? "]" ws
value ::= object | array | string | number | "true" ws | "false" ws | "null" ws
string ::= "\"" char* "\"" ws
char ::= [^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" hex hex hex hex)
number ::= "-"? int frac? exp? ws
int ::= "0" | [1-9] [0-9]*
frac ::= "." [0-9]+
exp ::= [eE] [+-]? [0-9]+
hex ::= [0-9a-fA-F]
ws ::= [ \t\n\r]*
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
