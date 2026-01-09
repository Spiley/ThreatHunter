#!/usr/bin/env bash
set -euo pipefail

# ===== instellingen =====
COMPOSE_DIR="/home/thpi/greenbone" # map waar docker compose in zit
ENVFILE="$COMPOSE_DIR/gvm.env"     # map met credentials
IFACE="eth0"                       # kan ook op wlan0 gezet worden

source "$ENVFILE"

# ===== gvm-cli helper via docker compose =====
GVM() {
  docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T --user gvm gvm-tools \
    gvm-cli --protocol GMP --gmp-username "$GVM_USER" --gmp-password "$GVM_PASS" \
    socket --socketpath /run/gvmd/gvmd.sock -X "$1"
}

# ===== wacht tot gvmd/GMP echt ready is =====
wait_for_gvm() {
  local timeout_secs="${1:-900}"   # 15 min default
  local interval_secs="${2:-10}"   # elke 10s proberen
  local start_ts now_ts

  start_ts="$(date +%s)"
  echo "⏳ Wachten tot GVM/GVMD ready is (timeout ${timeout_secs}s)..."

  while true; do
    if docker compose -f "$COMPOSE_DIR/docker-compose.yml" exec -T gvm-tools \
      sh -lc 'test -S /run/gvmd/gvmd.sock' >/dev/null 2>&1; then
      if GVM "<get_version/>" >/dev/null 2>&1; then
        echo "✅ GVM is ready."
        return 0
      fi
    fi

    now_ts="$(date +%s)"
    if (( now_ts - start_ts >= timeout_secs )); then
      echo "❌ Timeout: GVM is na ${timeout_secs}s nog niet ready."
      echo "Tip: docker compose -f \"$COMPOSE_DIR/docker-compose.yml\" logs --tail=200"
      return 1
    fi

    echo "… nog niet klaar, opnieuw in ${interval_secs}s"
    sleep "$interval_secs"
  done
}

# ===== wacht tot task klaar is =====
wait_for_task_done() {
  local task_id="$1"
  local interval_secs="${2:-30}"

  echo "📡 Scan draait… status wordt elke ${interval_secs}s gecontroleerd"

  while true; do
    STATUS_XML="$(GVM "<get_tasks task_id=\"$task_id\"/>")"

    STATUS="$(echo "$STATUS_XML" | grep -oP '<status>\K[^<]+' || true)"
    PROGRESS="$(echo "$STATUS_XML" | grep -oP '<progress>\K[^<]+' || true)"
    PROGRESS="${PROGRESS:-?}"

    TS="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$TS] Status: ${STATUS:-Onbekend} | Progress: ${PROGRESS}%"

    case "${STATUS:-}" in
      Done)
        echo "✅ Scan is KLAAR"
        break
        ;;
      Stopped|Interrupted)
        echo "⚠️ Scan is gestopt of onderbroken (status: $STATUS)"
        break
        ;;
    esac

    sleep "$interval_secs"
  done

  FINAL_REPORT_ID="$(echo "$STATUS_XML" | grep -oP 'report id="\K[^"]+' | head -n1 || true)"
  if [ -n "${FINAL_REPORT_ID:-}" ]; then
    echo "📄 Report ID: $FINAL_REPORT_ID"
  fi
}

# ===== helpers: bestaande target vinden =====
find_target_id_by_name() {
  local name="$1"
  local XML
  XML="$(GVM "<get_targets/>")"
  echo "$XML" | awk -v n="$name" 'BEGIN{RS="</target>"} $0 ~ "<name>"n"</name>" {
    match($0,/target id="[^"]+"/);
    if (RSTART>0) print substr($0,RSTART+11,RLENGTH-12)
  }' | head -n1
}

find_target_id_by_hosts() {
  local hosts="$1"
  local XML
  XML="$(GVM "<get_targets/>")"
  echo "$XML" | awk -v h="$hosts" 'BEGIN{RS="</target>"} $0 ~ "<hosts>"h"</hosts>" {
    match($0,/target id="[^"]+"/);
    if (RSTART>0) print substr($0,RSTART+11,RLENGTH-12)
  }' | head -n1
}

# ===== start =====
wait_for_gvm 900 10
echo "🚀 GVM ready, scan wordt uitgevoerd"

# 1. IP + subnet ophalen
CIDR="$(ip -o -4 addr show dev "$IFACE" | awk '{print $4}' | head -n1)"
if [ -z "${CIDR:-}" ]; then
  echo "❌ Geen IP gevonden op $IFACE"
  exit 1
fi

# subnet berekenen
NETWORK="$(python3 - <<EOF
import ipaddress
print(ipaddress.ip_interface("$CIDR").network)
EOF
)"
echo "✔ Gevonden subnet: $NETWORK"

NAME="test_target_${NETWORK//\//-}"

# 2a. Port list ID ophalen (probeer All IANA assigned TCP, anders pak de eerste)
PL_XML="$(GVM "<get_port_lists/>")"
PORT_LIST_ID="$(echo "$PL_XML" | awk 'BEGIN{RS="</port_list>"} /All IANA assigned TCP/{match($0,/id="[^"]+"/); print substr($0,RSTART+4,RLENGTH-5)}' | head -n1)"
if [ -z "${PORT_LIST_ID:-}" ]; then
  PORT_LIST_ID="$(echo "$PL_XML" | grep -oP 'port_list id="\K[^"]+' | head -n1)"
fi
if [ -z "${PORT_LIST_ID:-}" ]; then
  echo "❌ Kon geen port_list id vinden"
  exit 1
fi

# 2b. Target aanmaken (of bestaande pakken)
CREATE_TARGET_XML="$(GVM "<create_target><name>$NAME</name><hosts>$NETWORK</hosts><port_list id=\"$PORT_LIST_ID\"/></create_target>" || true)"

echo "---- create_target response ----"
echo "$CREATE_TARGET_XML"

TARGET_ID="$(echo "$CREATE_TARGET_XML" | grep -oP 'id="\K[^"]+' | head -n1 || true)"

if [ -n "${TARGET_ID:-}" ]; then
  echo "✅ Target aangemaakt met ID: $TARGET_ID"
else
  # Als hij al bestaat: ID opzoeken
  if echo "$CREATE_TARGET_XML" | grep -q 'Target exists already'; then
    echo "ℹ️ Target bestaat al, zoek bestaande TARGET_ID op…"
    TARGET_ID="$(find_target_id_by_name "$NAME" || true)"
    if [ -z "${TARGET_ID:-}" ]; then
      echo "ℹ️ Niet gevonden op naam, probeer op hosts ($NETWORK)…"
      TARGET_ID="$(find_target_id_by_hosts "$NETWORK" || true)"
    fi

    if [ -n "${TARGET_ID:-}" ]; then
      echo "✅ Bestaande target gevonden met ID: $TARGET_ID"
    else
      echo "❌ Target bestaat al, maar kon TARGET_ID niet vinden via get_targets."
      exit 1
    fi
  else
    echo "❌ Target niet aangemaakt (andere fout dan 'exists already')"
    exit 1
  fi
fi

# =============================
# 3. Full and fast scan starten
# =============================

# 3a. Scan config ID ophalen (Full and fast)
CFG_XML="$(GVM "<get_configs/>")"
CONFIG_ID="$(echo "$CFG_XML" | awk 'BEGIN{RS="</config>"} tolower($0) ~ /<name>full and fast<\/name>/{match($0,/id="[^"]+"/); print substr($0,RSTART+4,RLENGTH-5)}' | head -n1)"
if [ -z "${CONFIG_ID:-}" ]; then
  echo "⚠️ Kon config 'Full and fast' niet vinden, pak eerste beschikbare config als fallback."
  CONFIG_ID="$(echo "$CFG_XML" | grep -oP '<config id="\K[^"]+' | head -n1)"
fi
if [ -z "${CONFIG_ID:-}" ]; then
  echo "❌ Kon geen config id vinden"
  exit 1
fi
echo "✔ Scan config ID: $CONFIG_ID"

# 3b. Scanner ID ophalen (meestal OpenVAS Default)
SCN_XML="$(GVM "<get_scanners/>")"
SCANNER_ID="$(echo "$SCN_XML" | awk 'BEGIN{RS="</scanner>"} /OpenVAS Default/{match($0,/id="[^"]+"/); print substr($0,RSTART+4,RLENGTH-5)}' | head -n1)"
if [ -z "${SCANNER_ID:-}" ]; then
  echo "⚠️ Kon scanner 'OpenVAS Default' niet vinden, pak eerste beschikbare scanner als fallback."
  SCANNER_ID="$(echo "$SCN_XML" | grep -oP '<scanner id="\K[^"]+' | head -n1)"
fi
if [ -z "${SCANNER_ID:-}" ]; then
  echo "❌ Kon geen scanner id vinden"
  exit 1
fi
echo "✔ Scanner ID: $SCANNER_ID"

# 3c. Task aanmaken
TASK_NAME="task_full_fast_${NETWORK//\//-}_$(date +%Y%m%d_%H%M%S)"
CREATE_TASK_XML="$(GVM "<create_task><name>$TASK_NAME</name><config id=\"$CONFIG_ID\"/><target id=\"$TARGET_ID\"/><scanner id=\"$SCANNER_ID\"/></create_task>")"

echo "---- create_task response ----"
echo "$CREATE_TASK_XML"

TASK_ID="$(echo "$CREATE_TASK_XML" | grep -oP 'id="\K[^"]+' | head -n1)"
if [ -z "${TASK_ID:-}" ]; then
  echo "❌ Task niet aangemaakt (geen TASK_ID gevonden)"
  exit 1
fi
echo "✅ Task aangemaakt met ID: $TASK_ID"

# 3d. Task starten
START_XML="$(GVM "<start_task task_id=\"$TASK_ID\"/>")"
echo "---- start_task response ----"
echo "$START_XML"

REPORT_ID="$(echo "$START_XML" | grep -oP 'report_id="\K[^"]+' | head -n1 || true)"
if [ -n "${REPORT_ID:-}" ]; then
  echo "🚀 Scan is gestart! Report ID: $REPORT_ID"
else
  echo "🚀 Scan is gestart (geen report_id gevonden in response)."
fi

# 3e. Wachten tot scan klaar is
wait_for_task_done "$TASK_ID" 30