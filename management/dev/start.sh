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

# Initialize only once. The developer deploydb goal can modify database data.
existing="$(mysql -hskymoon-db -uroot -N -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='cloud' AND table_name='configuration'")"
if [[ "${existing}" != "1" ]]; then
  echo "SkyMoon: initializing development management database..."
  mvn -B -Pdeveloper -pl developer -Ddeploydb
fi

unset MYSQL_PWD

# The developer database initializer explicitly reads db.properties.override,
# but the running management server looks up a file named db.properties.
# Give Jetty a discoverable copy of the complete, container-specific config.
mkdir -p /opt/skymoon/conf
cp utils/conf/db.properties.override /opt/skymoon/conf/db.properties
chmod 600 /opt/skymoon/conf/db.properties
export CATALINA_HOME=/opt/skymoon

echo "SkyMoon: launching development management API on port 8080"
exec mvn -B -pl :cloud-client-ui jetty:run
