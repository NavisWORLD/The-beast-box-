// Native C++ process client for the real Python runtime; no shell evaluation.
#include <cerrno>
#include <cstdio>
#include <vector>
#ifdef _WIN32
#include <process.h>
#else
#include <unistd.h>
#endif
int main(int argc, char **argv) {
    if (argc < 3) {
        std::fprintf(stderr, "Usage: beast-client PYTHON DATA_DIR [runtime model options]\nJSON request on stdin\n");
        return 2;
    }
    std::vector<const char *> args = {argv[1], "-m", "beastbox", "runtime", "exchange", "--data-dir", argv[2]};
    for (int i = 3; i < argc; ++i) args.push_back(argv[i]);
    args.push_back(nullptr);
#ifdef _WIN32
    auto result = _spawnvp(_P_WAIT, argv[1], args.data());
    if (result != -1) return static_cast<int>(result);
#else
    execvp(argv[1], const_cast<char *const *>(args.data()));
#endif
    std::perror("Cannot start configured Beast Python runtime");
    return 2;
}
