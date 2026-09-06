#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p vendor
url=https://github.com/beeware/Python-Apple-support/releases/download/3.12-b9/Python-3.12-iOS-support.b9.tar.gz
curl --fail --location --retry 3 "$url" -o vendor/python.tar.gz
printf '%s  %s\n' a3be9e278c742911db54dd3045bd7451928813508771c9acf14b4af75294edd2 vendor/python.tar.gz | shasum -a 256 -c -
tar -xzf vendor/python.tar.gz -C vendor
