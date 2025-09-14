FROM alpine:latest AS cfst-builder
WORKDIR /app
RUN apk add curl jq
RUN <<EOF
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m | tr '[:upper:]' '[:lower:]')"
if [ "$ARCH" = "x86_64" ]; then
    ARCH="amd64"
elif [ "$ARCH" = "aarch64" ]; then
    ARCH="arm64"
fi

DOWNLOAD_URL=$(curl -fsSL "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest" | jq -r --arg os "$OS" --arg arch "$ARCH" '
        .assets[] 
        | select(.name | test($os) and test($arch)) 
        | .browser_download_url
    ')
curl -fsSL "$DOWNLOAD_URL" | tar -xzvf -
EOF

#####################################################################################
# Builder
FROM python:3-alpine AS builder
WORKDIR /build
COPY . .
RUN pip install --upgrade pip build
RUN python -m build --wheel

#####################################################################################
FROM python:3-alpine
LABEL maintainer="Jetsung Chan<i@jetsung.com>"

WORKDIR /app

RUN apk add --no-cache cronie

COPY --from=cfst-builder /app/cfst /usr/local/bin/cfst
COPY --from=builder /build/dist /app
COPY README.md /app/README.md

RUN mkdir ~/.cache

RUN pip install /app/*.whl && \
    rm -rf /app/*.whl && \
    rm -rf /var/cache/apk/*

RUN printf "%b" '#!'"/usr/bin/env sh\n \
if [ \"\$1\" = \"daemon\" ];  then \n \
 exec crond -n -s -m off \n \
else \n \
 exec -- \"\$@\"\n \
fi\n" >/entry.sh && chmod +x /entry.sh

VOLUME /app

ENTRYPOINT ["/entry.sh"]
