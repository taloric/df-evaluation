
.PHONY: all
all: eb-amd64

.PHONY: eb-amd64
eb-amd64: 
	CGO_ENABLED=0 GOOS=linux go build -o bin/x86_64/eb -a -ldflags '-extldflags "-static"' cmd/eb/main.go 

.PHONY: eb-arm64
eb-arm64:
	CGO_ENABLED=1 GOOS=linux GOARCH=arm CC=arm-linux-gnueabi-gcc go build -o bin/arm_64/eb -a -ldflags '-extldflags "-static"' cmd/eb/main.go


.PHONY: clean
clean: 
	rm -rf bin/eb