# adapted from https://github.com/lukebakken/stackoverflow-72318314-1466825

ARG RABBITMQ_VER

FROM rabbitmq:${RABBITMQ_VER}-alpine

# HOSTNAME is required for rabbitmq-server to start with persistent data
ENV RABBITMQ_PID_FILE=/var/lib/rabbitmq/mnesia/rabbitmq

ADD initialize_and_run.sh /usr/local/bin
RUN chmod 0755 /usr/local/bin/*.sh

ENTRYPOINT ["initialize_and_run.sh"]
CMD ["rabbitmq-server"]