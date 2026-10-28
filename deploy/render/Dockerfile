FROM ghcr.io/hkuds/deeptutor:1.6.15
COPY deploy/render /app/deploy/render
RUN pip install --no-cache-dir 'jsonschema>=4.23,<5' && \
    sed -i 's/deeptutor.api.main:app/deploy.render.backend:app/' /app/start-backend.sh
ENV BACKEND_HOST=127.0.0.1 FRONTEND_HOST=0.0.0.0
EXPOSE 10000
ENTRYPOINT ["/bin/bash", "/app/deploy/render/start.sh"]
