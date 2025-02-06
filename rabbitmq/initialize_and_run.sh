#!/bin/bash
# NOTE: file end of line characters must be LF, not CRLF (see https://stackoverflow.com/a/58220487/799921)

# NOTE:
# Without the initial sleep, you will probably hit this issue:
# https://github.com/docker-library/rabbitmq/issues/114
# https://github.com/docker-library/rabbitmq/issues/318
# adapted from https://github.com/lukebakken/stackoverflow-72318314-1466825

# initialize vhost and user if not already done
(sleep 10 && rabbitmqctl wait --timeout 60 "$RABBITMQ_PID_FILE" && \
    if ! rabbitmqctl list_users | grep -q "rabbit-user"; then \
        rabbitmqctl delete_user guest; \
        rabbitmqctl add_vhost rabbit-vhost ; \
        rabbitmqctl add_user rabbit-user "$(cat /run/secrets/rabbitmq-app-password)" ; \
        rabbitmqctl set_permissions -p rabbit-vhost rabbit-user  ".*" ".*" ".*" ; \
        echo "*** vhost rabbit-vhost and user rabbit-user created ***" ; 
    fi \
) &

docker-entrypoint.sh "$@"
