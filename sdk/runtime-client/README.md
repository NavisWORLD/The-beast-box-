# Runtime JSON interface v1

Any language capable of launching a process and reading/writing JSON can use
`python -m beastbox runtime exchange --data-dir PATH --model A`. Send one UTF-8
JSON object (maximum 16384 bytes) on stdin, then close stdin:

```json
{"schema":"beastbox-request-v1","operation":"chat","text":"Remember the sunflower"}
```

Operations: `chat` with `text`, or `inspect` and `init` without `text`.
Success returns `beastbox-response-v1`, `ok: true`, and the real runtime `result`.
Failure exits nonzero and writes a diagnostic on stderr. Reject responses unless
both process status and response schema indicate success. Unknown request fields
are rejected. Provider/model configuration belongs to the host command line;
the protocol has no shell, cloud-job or actuator authority operation.

C++17 and Rust clients here forward stdin/stdout without shell interpolation.
Build with `c++ -std=c++17 client.cpp -o beast-client-cpp` or
`rustc client.rs -o beast-client-rust`. Pass the installed Python executable and
data directory as separate arguments. These are native clients of the Python
runtime, not claims that the whole runtime has been ported to C++ or Rust.
