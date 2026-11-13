#!/bin/bash
#
# hourly: rebuild books whose alt text was saved in altpoet, then ack them
# needs ALTPOET_URL and EBOOKCONVERTER_API_KEY
# extra args are passed to ebookconverter (e.g. --dry-run)

API="${ALTPOET_URL}/api/documents/changed/"
RESP=$(curl -fsS -H "X-Api-Key: ${EBOOKCONVERTER_API_KEY}" "$API") || exit 1
LIST=$(echo "$RESP" | python3 -c 'import json,sys; print(",".join(json.load(sys.stdin)["items"]))')
BEFORE=$(echo "$RESP" | python3 -c 'import json,sys; print(json.load(sys.stdin)["before"])')

if [ "${LIST}x" = x ] ; then
    exit 0
fi

cd "${EBOOKCONVERTER_DIR:-/export/sunsite/users/gutenbackend/ebookconverter}"
~/.local/bin/pipenv run ebookconverter -v --range=${LIST} --build=all "$@" || exit 1

curl -fsS -X POST -H "X-Api-Key: ${EBOOKCONVERTER_API_KEY}" -H "Content-Type: application/json" \
    -d "{\"before\": \"${BEFORE}\"}" "$API"
