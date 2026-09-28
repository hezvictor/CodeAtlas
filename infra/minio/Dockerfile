ARG MINIO_BUILDER_IMAGE=golang@sha256:3d78beb141d98f42337f1252ecf2a5f20374109929a4c3f6817f9e4179cc0ae5
FROM ${MINIO_BUILDER_IMAGE} AS builder
ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOPROXY=https://goproxy.cn,https://proxy.golang.org,direct
RUN for attempt in 1 2 3; do \
      go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z && exit 0; \
    done; exit 1

FROM python@sha256:d1e9ca7c4e78d1e8ecadb5d44bfc8e956e7a65b659a9950f569f243d72b326d0
COPY --from=builder /go/bin/minio /usr/local/bin/minio
LABEL org.opencontainers.image.source="https://github.com/minio/minio" \
      org.opencontainers.image.version="RELEASE.2025-10-15T17-29-55Z" \
      org.opencontainers.image.licenses="AGPL-3.0-only"
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
