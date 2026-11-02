# SkyMoon Cloud: developer-mode management backend from THIS repository.
# Source build is deliberately used so future SkyMoon code changes are included.
# This is a development image, not a production-hardened management image.
FROM maven:3.9-eclipse-temurin-17

ENV DEBIAN_FRONTEND=noninteractive \
    MAVEN_OPTS="-Xmx3g --add-opens=java.base/java.lang=ALL-UNNAMED --add-exports=java.base/sun.security.x509=ALL-UNNAMED"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      default-mysql-client genisoimage ipmitool iproute2 \
      python3 python3-pip python3-mysqldb \
      libffi-dev libssl-dev sudo git curl ca-certificates uuid-runtime \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/skymoon
COPY . .

# Matches INSTALL.md's developer-mode Maven build, minus tests.
# This full build may require substantial RAM, CPU, disk, and time.
RUN mvn -B -Pdeveloper -DskipTests clean install

COPY management/dev/start.sh /usr/local/bin/skymoon-management-start
RUN chmod 755 /usr/local/bin/skymoon-management-start

EXPOSE 8080
CMD ["/usr/local/bin/skymoon-management-start"]
