COMPOSE_FILE:=Docker/docker-compose.yml
SERVICE:=p4bot
LIMIT ?= 3

.PHONY: up build down login p4status test_p4python exec logs

up:
	docker compose -f $(COMPOSE_FILE) up --build -d

build:
	docker compose -f $(COMPOSE_FILE) build

down:
	docker compose -f $(COMPOSE_FILE) down

login:
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE) bash -lc "chmod +x /scripts/login.sh && /scripts/login.sh"

p4status:
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE) bash -lc "/scripts/p4status.sh --limit $(LIMIT)"

test_p4python:
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE) bash -lc "python3 /scripts/test_p4python.py"

exec:
	# Usage: make exec CMD="<command>"
	@[ -n "$(CMD)" ] || (echo "Please set CMD, e.g. make exec CMD=\"bash -lc 'ls -la /scripts'\"" && false)
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE) bash -lc "$(CMD)"

logs:
	docker compose -f $(COMPOSE_FILE) logs -f
