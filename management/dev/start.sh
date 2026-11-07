#!/usr/bin/env bash
set -euo pipefail

: "${SKYMOON_DEV_DB_PASSWORD:?Missing application database password}"
: "${SKYMOON_DEV_DB_ROOT_PASSWORD:?Missing root database password}"

cd /opt/skymoon

# DatabaseCreator uses the override file AS THE ENTIRE DB configuration,
# not as a merge with the base db.properties. Start from the full base file
# to retain db.cloud.port/name, db.usage.port/name, JDBC settings and pool limits.
# Later duplicate keys in Java properties are deliberately overridden below.
cp utils/conf/db.properties utils/conf/db.properties.override

# Restrict the prototype to alphanumeric DB passwords to avoid Java-properties escaping.
for var in SKYMOON_DEV_DB_PASSWORD SKYMOON_DEV_DB_ROOT_PASSWORD; do
  value="${!var}"
  if [[ ! "${value}" =~ ^[A-Za-z0-9]+$ ]]; then
    echo "ERROR: ${var} must be alphanumeric for this developer-only bootstrap." >&2
    exit 1
  fi
done

node_ip="$(hostname -i | awk '{print $1}')"
cat >> utils/conf/db.properties.override <<EOF
cluster.node.IP=${node_ip}
db.cloud.host=skymoon-db
db.cloud.username=cloud
db.cloud.password=${SKYMOON_DEV_DB_PASSWORD}
db.root.password=${SKYMOON_DEV_DB_ROOT_PASSWORD}
db.usage.host=skymoon-db
db.usage.username=cloud
db.usage.password=${SKYMOON_DEV_DB_PASSWORD}
EOF
chmod 600 utils/conf/db.properties.override

export MYSQL_PWD="${SKYMOON_DEV_DB_ROOT_PASSWORD}"
mysql -hskymoon-db -uroot -e 'SELECT 1' >/dev/null

# Only initialize a truly empty schema; fail safely if initialization was interrupted.
# Do not run developer deploydb on a populated or partially initialized volume.
schema_action="$(bash management/dev/db-init-guard.sh)"
if [[ "$schema_action" == "initialize" ]]; then
  echo "SkyMoon: initializing empty development management database..."
  mvn -B -Pdeveloper -pl developer -Ddeploydb
else
  echo "SkyMoon: found existing management schema; leaving data intact."
fi

unset MYSQL_PWD

# The database initializer reads utils/conf/db.properties.override, but Jetty
# loads db.properties from client/target/conf via client/pom.xml extraClasspath.
# Maven's generate-resources phase regenerates target/conf/db.properties from
# client/conf/db.properties.in, which otherwise contains default localhost values.
# Add a same-named non-template file to client/conf: the final Ant copy task
# overwrites the generated defaults with these runtime connection settings.
cp utils/conf/db.properties.override client/conf/db.properties
cp utils/conf/db.properties.override client/target/conf/db.properties
chmod 600 client/conf/db.properties client/target/conf/db.properties

# Keep a fallback copy for tools that search catalina.home/conf as well.
mkdir -p /opt/skymoon/conf
cp utils/conf/db.properties.override /opt/skymoon/conf/db.properties
chmod 600 /opt/skymoon/conf/db.properties
export CATALINA_HOME=/opt/skymoon

echo "SkyMoon: launching development management API on port 8080"
exec mvn -B -pl :cloud-client-ui jetty:run
