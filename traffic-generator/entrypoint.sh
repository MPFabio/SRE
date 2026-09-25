set -e

if [ "$LOCUST_WEB" = "true" ]; then
    exec locust         --locustfile locustfile.py         --host "$LOCUST_HOST"         --autostart         --users "$LOCUST_USERS"         --spawn-rate "$LOCUST_SPAWN_RATE"
fi

if [ "$LOCUST_RUN_TIME" = "0" ]; then
    exec locust         --locustfile locustfile.py         --headless         --host "$LOCUST_HOST"         --users "$LOCUST_USERS"         --spawn-rate "$LOCUST_SPAWN_RATE"
fi

exec locust     --locustfile locustfile.py     --headless     --host "$LOCUST_HOST"     --users "$LOCUST_USERS"     --spawn-rate "$LOCUST_SPAWN_RATE"     --run-time "$LOCUST_RUN_TIME"
