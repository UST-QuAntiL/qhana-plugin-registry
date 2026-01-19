FROM python:3.12

LABEL org.opencontainers.image.source="https://github.com/UST-QuAntiL/qhana-plugin-registry"

WORKDIR /app

RUN useradd gunicorn


ENV FLASK_APP=qhana_plugin_registry
ENV FLASK_ENV=production
ENV PLUGIN_FOLDERS=/app/plugins:/app/extra-plugins:/app/git-plugins


# can be server or worker
ENV CONTAINER_MODE=server
ENV DEFAULT_LOG_LEVEL=INFO
ENV CONCURRENCY=2
ENV CELERY_WORKER_POOL=threads

# make directories and set user rights
RUN mkdir --parents /app/instance \
    && chown --recursive gunicorn /app && chmod --recursive u+rw /app/instance

# install proxy
ADD https://raw.githubusercontent.com/UST-QuAntiL/docker-localhost-proxy/v0.3/install_proxy.sh install_proxy.sh
RUN chmod +x install_proxy.sh && ./install_proxy.sh

# add localhost proxy files
ADD https://raw.githubusercontent.com/UST-QuAntiL/docker-localhost-proxy/v0.3/Caddyfile.template Caddyfile.template
RUN chown gunicorn Caddyfile.template
ADD https://raw.githubusercontent.com/UST-QuAntiL/docker-localhost-proxy/v0.3/start_proxy.sh start_proxy.sh
RUN chown gunicorn start_proxy.sh && chmod +x start_proxy.sh

# Wait for database
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.9.0/wait /wait
RUN chmod +x /wait


RUN python -m pip install poetry gunicorn

COPY --chown=gunicorn . /app

RUN python -m poetry export --without-hashes --extras=psycopg --extras=PyMySQL --format=requirements.txt -o requirements.txt && python -m pip install -r requirements.txt

VOLUME ["/app/instance"]

EXPOSE 8080

USER gunicorn

ENTRYPOINT ["sh", "-c", "./start_proxy.sh && python -m invoke start-docker"]
