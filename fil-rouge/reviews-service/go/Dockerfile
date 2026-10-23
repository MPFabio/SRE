FROM golang:1.26-alpine AS build

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY main.go .
RUN CGO_ENABLED=0 go build -o /reviews-service .

FROM alpine:3.22

COPY --from=build /reviews-service /reviews-service

USER 10001
EXPOSE 8086

ENTRYPOINT ["/reviews-service"]
