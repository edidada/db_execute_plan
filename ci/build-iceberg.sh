#!/usr/bin/env bash
set -euxo pipefail
cd upstream/iceberg
export ICEBERG_GIT_DIR
ICEBERG_GIT_DIR="$(git rev-parse --absolute-git-dir)"
chmod +x gradlew
./gradlew --init-script ../../ci/iceberg-submodule.init.gradle --no-daemon --max-workers=2 -DsparkVersions=3.5 -DflinkVersions= -DscalaVersion=2.12 \
  :iceberg-spark:iceberg-spark-runtime-3.5_2.12:shadowJar -x test
cd ../..
mapfile -t jars < <(find upstream/iceberg/spark/v3.5/spark-runtime/build/libs -name '*.jar' ! -name '*sources*' ! -name '*javadoc*')
test "${#jars[@]}" -eq 1
sha256sum "${jars[0]}" | tee artifacts/iceberg-runtime-sha256.txt
spark-submit --jars "${jars[0]}" tools/iceberg_demo.py
