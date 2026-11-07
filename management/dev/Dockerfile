# syntax=docker/dockerfile:1.7
# SkyMoon Cloud: developer-mode management backend built from THIS repository.
# Development only, not a production-hardened management server.
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
# The External provisioner executes the adapter directly, not via "python3".
RUN chmod 755 /opt/skymoon/extensions/DigitalOcean/digitalocean.py

# Build only the management web application, development database tooling,
# and their Maven dependencies. A full reactor build also runs unrelated
# apidocs generation, which failed after all management components succeeded.
# Keep Maven's local repository inside the image because developer mode runs
# Maven again at container startup for database setup and Jetty.
RUN mvn -B -Pdeveloper -DskipTests \
      -pl :cloud-client-ui,:cloud-developer -am \
      clean install

COPY management/dev/start.sh /usr/local/bin/skymoon-management-start
RUN chmod 755 /usr/local/bin/skymoon-management-start

EXPOSE 8080
CMD ["/usr/local/bin/skymoon-management-start"]
