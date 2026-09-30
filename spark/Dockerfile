FROM maven:3.9-eclipse-temurin-17 AS deps
WORKDIR /dep
COPY pom.xml .
RUN mkdir -p /jars \
    && mvn -B -q dependency:copy-dependencies -DincludeScope=runtime -DoutputDirectory=/jars

FROM bitnamilegacy/spark:3.5.3

USER root
RUN pip install --no-cache-dir psycopg2-binary==2.9.10 \
    && mkdir -p /tmp/spark/checkpoints && chown -R 1001:1001 /tmp/spark
COPY --from=deps /jars/ /opt/bitnami/spark/jars/
COPY jobs /jobs
USER 1001

WORKDIR /jobs
CMD ["spark-submit", "--help"]
