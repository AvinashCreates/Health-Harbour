FROM golang:1.23-alpine AS build

WORKDIR /src
RUN apk add --no-cache git
COPY go.mod ./
RUN go mod download
COPY . ./
RUN CGO_ENABLED=0 GOOS=linux go build \
    -trimpath \
    -ldflags="-s -w" \
    -o /out/fabric-gateway-adapter .

FROM alpine:3.22

RUN apk add --no-cache ca-certificates wget \
    && addgroup -S -g 10001 app \
    && adduser -S -D -H -u 10001 -G app app
COPY --from=build --chown=10001:10001 /out/fabric-gateway-adapter /usr/local/bin/fabric-gateway-adapter

ENV LISTEN_ADDR=0.0.0.0:8080
EXPOSE 8080
USER 10001:10001

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/health || exit 1

ENTRYPOINT ["/usr/local/bin/fabric-gateway-adapter"]
