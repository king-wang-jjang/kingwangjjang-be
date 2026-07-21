# Windows Ollama Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure Ollama on Windows PC `100.118.130.61` to start without user login, restart after failure, and expose a verified API on TCP 11434.

**Architecture:** Install NSSM through the existing Chocolatey installation and register the existing Ollama executable as a LocalSystem Windows service. Pass explicit host and model-path environment variables to avoid dependence on an interactive user profile, then configure delayed automatic start and Windows recovery actions.

**Tech Stack:** Windows OpenSSH, PowerShell, Chocolatey, NSSM, Ollama

---

### Task 1: Capture the pre-change state

- [ ] Record the Ollama executable path, model directory, existing service state, port 11434 state, and firewall rule state.
- [ ] Confirm the SSH session is elevated and Chocolatey is available.

### Task 2: Install and configure the service

- [ ] Install NSSM with `choco install nssm -y --no-progress` if `nssm.exe` is absent.
- [ ] Register service `Ollama` with executable `C:\Users\hwanj\AppData\Local\Programs\Ollama\ollama.exe` and argument `serve`.
- [ ] Configure the service for `LocalSystem`, delayed automatic startup, and environment values `OLLAMA_HOST=100.118.130.61:11434` and `OLLAMA_MODELS=C:\Users\hwanj\.ollama\models`.
- [ ] Configure Windows recovery actions to restart after 5 seconds on repeated failures.
- [ ] Create or enable the TCP 11434 inbound firewall rule.

### Task 3: Start and validate

- [ ] Start the service and confirm it reaches `Running` state.
- [ ] Verify `http://127.0.0.1:11434/api/tags` from the AI PC.
- [ ] Verify `http://100.118.130.61:11434/api/tags` from the current PC.
- [ ] Stop the underlying Ollama process and confirm Windows restores the service automatically.
- [ ] Re-run both API checks and capture final service configuration.

### Task 4: Rollback if validation fails

- [ ] Stop and remove only the `Ollama` NSSM service and its firewall rule.
- [ ] Leave the Ollama executable, model directory, and user environment variables untouched.
