# Variables
COMPOSE = docker compose
SERVICE_NAME = chatbot
GREEN = \033[0;32m
RED = \033[0;31m
YELLOW = \033[1;33m
NC = \033[0m # No Color
TIMESTAMP = $(shell date -u '+%Y-%m-%d %H:%M:%S')

# Function to get container ID safely
define get_container_id
$(shell docker ps -qf "name=pdf-chatbot-api-chatbot" 2>/dev/null)
endef

# Function to check if container exists and is running
define check_container
	@if [ -z "$(call get_container_id)" ]; then \
		echo "$(RED)Error: Container is not running$(NC)"; \
		exit 1; \
	fi
endef

.PHONY: help build up down restart logs clean status shell models debug check-logs

build:
	@echo "$(GREEN)Building container...$(NC)"
	$(COMPOSE) build
	@echo "$(GREEN)Build complete$(NC)"

up:
	@echo "$(GREEN)Starting container... $(NC)"
	$(COMPOSE) up -d
	@echo "$(YELLOW)[$(TIMESTAMP)] Waiting for container to start...$(NC)"
	@sleep 5
	@container_id=$$(docker ps -qf "name=pdf-chatbot-api-chatbot"); \
	if [ -z "$$container_id" ]; then \
		echo "$(RED)Container failed to start$(NC)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)Container started with ID: $$container_id$(NC)"; \
	echo "$(YELLOW)Waiting for Ollama to start...$(NC)"; \
	for i in $$(seq 1 60); do \
		if docker exec $$container_id curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then \
			echo "$(GREEN)Ollama is ready!$(NC)"; \
			break; \
		fi; \
		if [ $$i -eq 60 ]; then \
			echo "$(RED)Ollama failed to start$(NC)"; \
			exit 1; \
		fi; \
		echo "$(YELLOW)Waiting for Ollama ($$i/60)...$(NC)"; \
		sleep 1; \
	done; \
	echo "$(YELLOW)Waiting for models to download... This may take several minutes...$(NC)"; \
	while true; do \
		if docker exec $$container_id test -f /tmp/.models_ready 2>/dev/null; then \
			echo "$(GREEN)✓ Models download completed!$(NC)"; \
			break; \
		fi; \
		echo "$(YELLOW)⏳ Current models status ($(TIMESTAMP)):$(NC)"; \
		docker exec $$container_id curl -s http://localhost:11434/api/tags 2>/dev/null | \
			jq -r '.models[]? | "  - \(.name): \(.size/1024/1024|round) MB"' 2>/dev/null || \
			echo "  No models available yet"; \
		sleep 10; \
	done; \
	echo "$(YELLOW)Waiting for FastAPI to start...$(NC)"; \
	for i in $$(seq 1 12); do \
		if docker exec $$container_id curl -s http://localhost:8000/health > /dev/null 2>&1; then \
			echo "$(GREEN)✓ FastAPI is running!$(NC)"; \
			echo "$(GREEN)✓ All services are ready!$(NC)"; \
			exit 0; \
		fi; \
		echo "$(YELLOW)Waiting for FastAPI ($$i/12)...$(NC)"; \
		sleep 5; \
	done; \
	echo "$(RED)❌ Services failed to initialize properly$(NC)"; \
	exit 1

# Add a new target to show download progress
download-progress:
	@if [ -z "$(CONTAINER_ID)" ]; then \
		echo "$(RED)No running container found$(NC)"; \
		exit 1; \
	fi
	@while true; do \
		clear; \
		echo "$(YELLOW)Current Download Status:$(NC)"; \
		if docker exec $(CONTAINER_ID) test -f /tmp/.models_downloading; then \
			echo "$(YELLOW)⏳ Models are downloading:$(NC)"; \
			docker exec $(CONTAINER_ID) curl -s http://localhost:11434/api/tags | \
				jq -r '.models[] | "  - \(.name): \(.size/1024/1024) MB"' 2>/dev/null || \
				echo "  No models available yet"; \
		elif docker exec $(CONTAINER_ID) test -f /tmp/.models_ready; then \
			echo "$(GREEN)✓ All models downloaded:$(NC)"; \
			docker exec $(CONTAINER_ID) curl -s http://localhost:11434/api/tags | \
				jq -r '.models[] | "  - \(.name): \(.size/1024/1024) MB"'; \
			break; \
		else \
			echo "$(RED)! Download status unknown$(NC)"; \
		fi; \
		sleep 2; \
	done

down:
	@echo "$(RED)Stopping container...$(NC)"
	$(COMPOSE) down

restart: down up

clean:
	@echo "$(RED)Removing container and volumes...$(NC)"
	$(COMPOSE) down -v
	@echo "$(GREEN)Cleanup complete$(NC)"

status:
	@container_id=$$(docker ps -qf "name=pdf-chatbot-api-chatbot"); \
	if [ -z "$$container_id" ]; then \
		echo "$(RED)Container is not running$(NC)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Checking services status... $(NC)"; \
	echo; \
	echo "$(YELLOW)Container Status: $(NC)"; \
	docker ps -f "id=$$container_id"; \
	echo; \
	echo "$(YELLOW)Models Status: $(NC)"; \
	if docker exec $$container_id test -f /tmp/.models_downloading 2>/dev/null; then \
		echo "$(YELLOW)⏳ Models are currently downloading:$(NC)"; \
		docker exec $$container_id curl -s http://localhost:11434/api/tags | \
			jq -r '.models[]? | "  - \(.name): \(.size/1024/1024|round) MB"' 2>/dev/null || \
			echo "  No models available yet"; \
	elif docker exec $$container_id test -f /tmp/.models_ready 2>/dev/null; then \
		echo "$(GREEN)✓ Models are ready:$(NC)"; \
		docker exec $$container_id curl -s http://localhost:11434/api/tags | \
			jq -r '.models[]? | "  - \(.name): \(.size/1024/1024|round) MB"' 2>/dev/null; \
	else \
		echo "$(RED)! Models status unknown$(NC)"; \
	fi; \
	echo; \
	echo "$(YELLOW)Service Status:$(NC)"; \
	if docker exec $$container_id curl -s http://localhost:8000/health > /dev/null 2>&1; then \
		echo "$(GREEN)✓ FastAPI is running$(NC)"; \
	else \
		echo "$(RED)✗ FastAPI is not running$(NC)"; \
	fi; \
	if docker exec $$container_id curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then \
		echo "$(GREEN)✓ Ollama is running$(NC)"; \
	else \
		echo "$(RED)✗ Ollama is not running$(NC)"; \
	fi

logs:
	@container_id=$$(docker ps -qf "name=pdf-chatbot-api-chatbot"); \
	if [ -z "$$container_id" ]; then \
		echo "$(RED)Container is not running$(NC)"; \
		exit 1; \
	fi; \
	docker logs -f $$container_id

shell:
	@container_id=$$(docker ps -qf "name=pdf-chatbot-api-chatbot"); \
	if [ -z "$$container_id" ]; then \
		echo "$(RED)Container is not running$(NC)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)Opening shell in container...$(NC)"; \
	docker exec -it $$container_id /bin/bash

models:
	@echo "$(GREEN)Pulling AI models...$(NC)"
	@if [ -z "$(CONTAINER_ID)" ]; then \
		echo "$(RED)No running container found$(NC)"; \
		exit 1; \
	fi
	@docker exec $(CONTAINER_ID) curl -X POST http://localhost:11434/api/pull -d '{"name": "llama3.2:3b"}'
	@docker exec $(CONTAINER_ID) curl -X POST http://localhost:11434/api/pull -d '{"name": "nomic-embed-text"}'

debug: down
	@echo "$(YELLOW)Starting in debug mode...$(NC)"
	$(COMPOSE) up

check-logs:
	@echo "$(YELLOW)Checking all log files...$(NC)"
	@if [ -z "$(CONTAINER_ID)" ]; then \
		echo "$(RED)No running container found$(NC)"; \
		exit 1; \
	fi
	@echo "\n$(GREEN)Supervisor Log:$(NC)"
	@docker exec $(CONTAINER_ID) cat /var/log/supervisor/supervisord.log
	@echo "\n$(GREEN)Ollama Log:$(NC)"
	@docker exec $(CONTAINER_ID) cat /var/log/supervisor/ollama.out.log
	@echo "\n$(GREEN)FastAPI Log:$(NC)"
	@docker exec $(CONTAINER_ID) cat /var/log/supervisor/fastapi.out.log
	@echo "\n$(GREEN)Error Logs:$(NC)"
	@docker exec $(CONTAINER_ID) cat /var/log/supervisor/ollama.err.log
	@docker exec $(CONTAINER_ID) cat /var/log/supervisor/fastapi.err.log

api-logs:
	@echo "\n$(GREEN)FastAPI Log:$(NC)"
	@container_id=$$(docker ps -qf "name=pdf-chatbot-api-chatbot"); \
	docker exec $$container_id cat /var/log/supervisor/fastapi.out.log

api-err-logs:
	@echo "\n$(GREEN)FastAPI Error Logs:$(NC)"
	@container_id=$$(docker ps -qf "name=pdf-chatbot-api-chatbot"); \
	@docker exec $$container_id cat /var/log/supervisor/fastapi.err.log

# Helper target to show container ID
id:
	@echo "Container ID: $(CONTAINER_ID)"
