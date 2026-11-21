# =============================================================================
# Makefile — SmartHome-Boot2Root helpers
# =============================================================================

COMPOSE   := docker compose
IMAGE     := smarthome-boot2root:latest
CONTAINER := smarthome-lab

.PHONY: build up down reset verify logs shell clean

## build: Build the self-contained Docker image
build:
	$(COMPOSE) build

## up: Start the lab (detached)
up:
	$(COMPOSE) up -d
	@echo ""
	@echo "  Web app : http://127.0.0.1:5000"
	@echo "  SSH     : ssh -p 2222 automation@127.0.0.1"
	@echo ""
	@echo "Waiting for healthcheck..."
	@sleep 8
	@docker inspect --format='{{.State.Health.Status}}' $(CONTAINER) 2>/dev/null || true

## down: Stop and remove the lab container
down:
	$(COMPOSE) down

## reset: Destroy container + volumes, rebuild and start fresh (new flags)
reset:
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) build
	$(COMPOSE) up -d

## verify: Run the automated end-to-end exploit verification script
verify: up
	@echo "[*] Running end-to-end verification..."
	@sleep 5
	python3 scripts/verify_chain.py

## logs: Tail container logs
logs:
	docker logs -f $(CONTAINER)

## shell: Drop a root shell into the running container (host-only debug)
shell:
	docker exec -it $(CONTAINER) /bin/sh

## clean: Remove image and all containers
clean:
	$(COMPOSE) down --rmi all -v --remove-orphans

