# Team Handoff — Remaining Work (Phases 8 & 9)

This document tells a teammate everything needed to finish the project:
how to get the code, how to run it, what is already done, what is left,
and the exact prompt to give an AI coding assistant.

**Repository:** https://github.com/BHAVYA123REDDY/Data-Lineage-Tracker-with-Auto-Rollback
**Default branch:** `main`
**Latest commit at handoff:** `fa72cbc` (Phase 7 — Docker)

---

## 1. How to get the code

**Recommended: clone the repository.** It contains everything that matters and
the full commit history, which proves who built which phase.

```bash
git clone https://github.com/BHAVYA123REDDY/Data-Lineage-Tracker-with-Auto-Rollback.git
cd Data-Lineage-Tracker-with-Auto-Rollback
```

> The repository is the single source of truth. Do **not** work from a ZIP and
> then try to merge — you will lose history and create conflicts.

If you must send a ZIP (for example, someone has no GitHub account), create a
clean snapshot of only the tracked files:

```bash
git archive --format=zip -o Data-Lineage-Tracker.zip HEAD
```

**Never** ZIP the project folder by hand. It would include `.venv/` (hundreds of
MB), `lineage.db` (local data), `app.log` and `__pycache__/` — all of which are
deliberately excluded by `.gitignore`.

---

## 2. What is already finished

| Phase | Commit | What it added |
|---|---|---|
| 1 | `53a2d9f` | Minimal Flask site with dashboard placeholder cards |
| 2 | `ce83d3f` | SQLite layer, version history tables, seed data, 10 tests |
| 3 | `43ab166` | Data lineage tracking, simulated pipeline runs, dashboard views, 23 tests |
| 4 | `487ab10` | Automatic rollback to last successful version + rollback history, 21 tests |
| 5 | `ec61bee` | Source health cards, activity feed, `/logs` page, `/health`, JSON error handling, 45 tests |
| 6 | `bf2eccd` | README, MIT LICENSE, real screenshots in `docs/screenshots/` |
| 7 | `fa72cbc` | `Dockerfile`, `docker-compose.yml`, entrypoint, env-var config, 23 tests |

**Current test count: 122 tests across 5 files — all passing.**

---

## 3. What is left to do

### Phase 8 — Jenkins CI/CD pipeline (required)

Deliverables:

1. `Jenkinsfile` at the repository root using **Declarative Pipeline**.
2. Pipeline stages, in order:
   - **Checkout** — pull the repo
   - **Set up** — create a virtual environment and `pip install -r requirements.txt`
   - **Test** — run all five test files and fail the build if any test fails
   - **Build image** — `docker build -t data-lineage-tracker:${BUILD_NUMBER} .`
   - **Deploy** — start the container
   - **Smoke test** — call `GET /health` and `POST /api/simulate` with
     `force_failure: true`, then assert `rolled_back == true`
   - **post** section — archive results, dump logs on failure, and clean up the
     container in `always`
3. Jenkins running locally, a Pipeline job created, and one **green** build.
4. Commit and push: `Phase 8: Add Jenkins CI/CD pipeline with tests, Docker build and health smoke test`

### Phase 9 — Kubernetes (optional, only if it works on the laptop)

Deliverables (only attempt if memory allows):

1. `k8s/deployment.yaml` — 1 replica, resource requests/limits, `/health`
   readiness and liveness probes, `LINEAGE_DB_PATH` on a volume.
2. `k8s/service.yaml` — `NodePort` so it can be opened from Windows.
3. Enabled Kubernetes inside Docker Desktop (Settings → Kubernetes).
4. `kubectl apply -f k8s/`, verify with `kubectl get pods` and `kubectl port-forward`.
5. Commit and push: `Phase 9: Add Kubernetes deployment and service manifests`

> Honest constraint: this laptop has **8 GB RAM**. Running Docker Desktop +
> Jenkins + Kubernetes at the same time will be very slow. Do Phase 9 with
> Jenkins stopped, and if it becomes unusable, document it in the README instead
> of forcing it — a clearly explained "not practical on this hardware" is a
> perfectly good answer for the college submission.

---

## 4. Setting up the machine (Windows, from scratch)

### Prerequisites

- Python 3.9+ (tick **Add Python to PATH** in the installer)
- Git
- Docker Desktop (download only from https://www.docker.com/products/docker-desktop/)
  - After installing, **open Docker Desktop and wait for "Engine running"**, or
    every Docker command fails with
    `failed to connect to the docker API ... is the daemon running`
- Java 17+ — only needed for Jenkins. Installing **Jenkins in Docker** avoids
  this completely (recommended).

### First run of the application

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe seed.py          # creates lineage.db + sample data
.venv\Scripts\python.exe app.py           # http://127.0.0.1:5000
```

`lineage.db` is **not** in the repository (databases are ignored on purpose), so
`seed.py` must be run once. It is idempotent — running it twice changes nothing.

### Run all tests (this is what CI does)

```powershell
.venv\Scripts\python.exe test_database.py
.venv\Scripts\python.exe test_pipeline.py
.venv\Scripts\python.exe test_rollback.py
.venv\Scripts\python.exe test_app.py
.venv\Scripts\python.exe test_config.py
```

Every file prints `[PASS]`/`[FAIL]` per check and exits with code `0` when green.

### Run it in Docker instead

```powershell
docker compose up -d --build
docker compose ps            # should say (healthy)
docker compose logs -f
docker compose down          # stop, data kept
```

### Starting Jenkins in Docker (no Java install needed)

```powershell
docker volume create jenkins-home
docker run -d --name jenkins -p 8080:8080 -p 50000:50000 `
  -v jenkins-home:/var/jenkins_home `
  -v //var/run/docker.sock:/var/run/docker.sock `
  jenkins/jenkins:lts-jdk17
```

Then open http://127.0.0.1:8080, unlock with the initial admin password
(`docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword`),
install the **suggested plugins** plus **Docker Pipeline**, and create a
**Pipeline** job pointing at the repository (Jenkins reads `Jenkinsfile` from Git).

> Close other memory-hungry apps while Jenkins runs. Stop Jenkins with
> `docker stop jenkins` when you are finished for the day.

#### ⚠️ Known gotcha: the Jenkins container has no `docker` command

The official `jenkins/jenkins` image **does not include the Docker CLI**. Mounting
the socket (`-v //var/run/docker.sock:/var/run/docker.sock`) lets a container talk
to the host engine, but only if a `docker` binary exists inside it. So a
`Jenkinsfile` that runs `docker build` will fail with
`docker: not found` on the first build.

Pick one of these, and **verify it before writing the pipeline**:

- **Option 1 (simplest):** install the CLI into the running container and run
  Jenkins as root so it can use the mounted socket.
  ```powershell
  docker rm -f jenkins
  docker run -d --name jenkins -u root -p 8080:8080 -p 50000:50000 `
    -v jenkins-home:/var/jenkins_home `
    -v //var/run/docker.sock:/var/run/docker.sock `
    jenkins/jenkins:lts-jdk17
  docker exec -u root jenkins bash -c "apt-get update && apt-get install -y --no-install-recommends docker.io && docker --version"
  docker exec jenkins docker ps
  ```
  If `docker ps` lists the host containers, the pipeline can build images.
  Note: this install is lost if the container is deleted (the volume only keeps
  `/var/jenkins_home`), so repeat it after recreating the container — or build a
  tiny custom image with the CLI baked in.

- **Option 2 (no Docker inside Jenkins):** keep Jenkins purely as the CI runner —
  it sets up Python, runs the 122 tests, and archives the results. Do the image
  build and container smoke test locally (they already work). This is perfectly
  acceptable for a college submission and uses less memory.

Agree with the team which option you are using **before** starting Phase 8, and
write the `Jenkinsfile` for that option so the build goes green on the first try.

---

## 5. Project layout

```
app.py                  Flask app: pages, JSON API, error handling, logging
database.py             SQLite layer: schema + all read/write helpers
pipeline.py             Pipeline simulation, lineage graph, activity log
rollback.py             Automatic rollback engine + AUTO_ROLLBACK_ENABLED switch
seed.py                 Sample demo data (idempotent)
test_database.py        10 tests
test_pipeline.py        23 tests
test_rollback.py        21 tests
test_app.py             45 tests
test_config.py          23 tests
Dockerfile              Container image
docker-compose.yml      One-command container start with a data volume
docker-entrypoint.sh    Seeds data if empty, then starts the app
templates/              index.html, logs.html, error.html
static/style.css        All styling
docs/screenshots/       Dashboard and logs screenshots used by the README
README.md               Full project documentation
HANDOFF.md              Team handoff guide + ready-to-use prompts for phases 8-9
```

---

## 6. How the app is wired (short version)

- A **data source** (`customers_csv`, `orders_api`) has a **lineage chain**:
  `source → ingest_<source> → transform_<source> → warehouse_<source>`.
- Each pipeline run creates a new **data version** (`data_versions`) with status
  `active`, `failed` or `rolled_back`, and a **pipeline run** row (`pipeline_runs`).
- If a run fails and `AUTO_ROLLBACK_ENABLED` is true, `rollback.py` finds the
  newest `active` version for that source, marks the bad one `rolled_back`, and
  writes a row to `rollback_logs`. **Nothing is ever deleted.**
- Environment variables: `HOST`, `PORT`, `LINEAGE_DB_PATH`, `AUTO_ROLLBACK_ENABLED`,
  `FLASK_DEBUG`, `LINEAGE_LOG_PATH`.

Key endpoints: `GET /`, `GET /logs`, `GET /health`, `GET /api/status`,
`/api/versions`, `/api/runs`, `/api/lineage`, `/api/rollbacks`, `/api/current`,
`/api/logs`, `/api/config`, `POST /api/simulate`, `POST /api/rollback`.

---

## 7. Ground rules (please follow these)

1. **Never** force-push, reset, or delete existing commits. Add work on top.
2. **One phase at a time.** Finish, test, commit, push, then move on.
3. Every phase must end with: all tests green → `git status` clean →
   commit named `Phase N: <what changed>` → `git push origin main` → confirm the
   push output and the commit ID.
4. **Never** commit `lineage.db`, `app.log` or `.venv/`.
5. Import secrets and tokens only from environment variables — never hardcode
   passwords, and never paste a GitHub token into a file in the repo.
6. Do not delete or rewrite files from earlier phases unless a test proves they
   must change. If a test expectation must change, update the test deliberately
   and explain why in the commit message.
7. Where relevant, keep the DevOps theme (lineage, versioning, rollback) —
   Phase 8 should use the `/health` and rollback endpoints as its smoke test
   rather than inventing unrelated checks.

---

## 8. Ready-to-paste prompt for the AI assistant (Phase 8)

> Copy everything in the box below into the AI coding assistant, opening it in
> the project folder.

```text
Continue work on my DevOps PBL project "Data Lineage Tracker with Auto Rollback"
(repository: https://github.com/BHAVYA123REDDY/Data-Lineage-Tracker-with-Auto-Rollback,
branch: main, latest commit: fa72cbc).

Phases 1-7 are already complete and pushed. The stack is Python 3 + Flask,
SQLite (no ORM), vanilla HTML/CSS/JS, Docker + Docker Compose. There are 122
tests across test_database.py, test_pipeline.py, test_rollback.py, test_app.py
and test_config.py, and all of them pass. Read README.md first for the full
picture.

Now do **Phase 8: Jenkins CI/CD pipeline**. Requirements:

1. First check the environment (docker --version, docker info, whether Jenkins
   is installed or running, whether Java is available) and show me the results
   before changing any files. If Jenkins is not running, tell me the exact
   commands to start it in Docker and wait for me to confirm it is up.
   - Important gotcha: the official jenkins/jenkins image has NO docker CLI, so a
     pipeline that runs `docker build` fails with "docker: not found" unless we
     install the CLI inside the Jenkins container (and run it as root so it can
     use the mounted /var/run/docker.sock). Verify `docker exec jenkins docker ps`
     works before writing the pipeline. If that is too heavy for this 8 GB
     laptop, use the fallback: Jenkins runs the 122 tests only, and the Docker
     build + container smoke test stay as local steps (they already work). Ask
     me which option I want.
2. Create a Jenkinsfile at the repository root using Declarative Pipeline with
   these stages: Checkout, Install dependencies, Run all 122 tests,
   Build Docker image, Start container, Smoke test, Clean up.
   - Tests: run each of the five test files; fail the build if any exits non-zero.
   - Smoke test: call GET /health and POST /api/simulate with
     {"source_name":"customers_csv","force_failure":true}, then assert that the
     response has rolled_back == true. This proves the auto-rollback feature
     works in the pipeline.
   - Use a post { always { ... } } block to dump container logs and remove the
     test container. Archive test output.
   - Tag the image with the Jenkins BUILD_NUMBER and also :latest.
   - Keep it lightweight: this laptop has 8 GB RAM, so do not run more than one
     container at a time.
3. Help me create the Jenkins Pipeline job (from SCM, reading Jenkinsfile from
   the repo), then run one build and show me the result.
4. Run the full local test suite again to confirm nothing regressed.
5. Show git status, commit with the message
   "Phase 8: Add Jenkins CI/CD pipeline with tests, Docker build and health smoke test",
   push to origin main, and then verify the push really landed (git log
   origin/main and the GitHub API). Report the branch and the commit ID.

Rules I want you to follow:
- Give me ONE step at a time and wait for me to reply "S" or "Done" before the
  next step. Provide exact commands and file paths.
- Never delete, overwrite, reset or force-push existing work. Add on top of it.
- Never hardcode or ask me for passwords or tokens. If authentication is needed,
  guide me to do it securely myself.
- Do not claim a command succeeded unless you actually saw it succeed, and never
  claim a commit or push worked unless the output confirms it.
- Keep everything lightweight for an 8 GB / i5 laptop. No heavy dependencies —
  the only Python dependency is Flask, and please keep it that way.
- Explain any error in simple language before fixing it.
- Also update README.md (roadmap table, CI section) as part of this phase.
```

---

## 9. Ready-to-paste prompt for the AI assistant (Phase 9, optional)

```text
Continue my DevOps PBL project "Data Lineage Tracker with Auto Rollback"
(repository: https://github.com/BHAVYA123REDDY/Data-Lineage-Tracker-with-Auto-Rollback,
branch: main). Phases 1-8 are complete and pushed: Flask + SQLite app, 122
passing tests, Docker image, docker-compose.yml, and a working Jenkins pipeline.

Now attempt **Phase 9: Kubernetes deployment**, but only if it is genuinely
practical on this laptop (Intel i5, 8 GB RAM, Docker Desktop on Windows 10).

1. First check whether Kubernetes is available (kubectl version --client,
   kubectl config current-context, kubectl cluster-info) and report the result.
   If it is not enabled, tell me how to enable it in Docker Desktop and wait for
   my confirmation.
2. Create k8s/deployment.yaml (1 replica, CPU/memory requests and limits suited
   to a small laptop, /health readiness and liveness probes, LINEAGE_DB_PATH on a
   persistent volume or emptyDir, and a non-root securityContext).
3. Create k8s/service.yaml using NodePort so I can reach it from Windows.
   Optionally add a ConfigMap for AUTO_ROLLBACK_ENABLED.
4. Apply the manifests, verify with kubectl get pods / kubectl get svc /
   kubectl describe, then demonstrate the app loading and the auto-rollback
   working through kubectl port-forward.
5. If memory pressure makes it unusable, STOP and tell me honestly, then instead
   write a short "Kubernetes (not practical on this hardware)" section in the
   README explaining what would be needed — do not pretend it worked.
6. Update README.md (roadmap, Kubernetes section), run the full test suite again,
   show git status, commit with
   "Phase 9: Add Kubernetes deployment and service manifests", push to origin main
   and verify the push landed. Report branch and commit ID.

Follow the same rules as before: one step at a time and wait for "S"/"Done",
never force-push or delete existing work, never hardcode secrets, keep it
lightweight, and only report success you actually observed.
```

---

## 10. Definition of done (checklist for each remaining phase)

- [ ] Code written and consistent with the existing style
- [ ] All five test files run and exit with code `0`
- [ ] Live check performed (browser or `curl`/`Invoke-RestMethod`) and its real output pasted
- [ ] `git status` shows only intended files; no `*.db`, `*.log` or `.venv/`
- [ ] `README.md` roadmap updated for the phase
- [ ] Commit message follows `Phase N: ...`
- [ ] `git push origin main` output shows the commit ID
- [ ] Push verified independently (for example
      `https://api.github.com/repos/BHAVYA123REDDY/Data-Lineage-Tracker-with-Auto-Rollback/commits/main`)
- [ ] Branch and commit ID reported back to the team

---

## 11. Quick troubleshooting

| Symptom | Cause and fix |
|---|---|
| `failed to connect to the docker API ... daemon running` | Docker Desktop is not started. Open it and wait for **Engine running**. |
| `docker: port is already allocated` | Port 5000 is taken. Use `-p 8080:5000`, or stop the other container. |
| Dashboard is empty | `lineage.db` was never seeded. Run `.venv\Scripts\python.exe seed.py`. |
| `ModuleNotFoundError: flask` | Virtual environment not used or dependencies missing. Run `.venv\Scripts\python.exe -m pip install -r requirements.txt`. |
| `Site can't be reached` in the browser | The server is not running. Start `app.py` or the container. |
| Jenkins container exits immediately | Not enough memory. Stop Docker containers you do not need and restart Jenkins. |
| `error: unable to read askpass` / push asks for password | Use a GitHub Personal Access Token as the password, or the Git Credential Manager prompt. Never store it in a file in the repo. |
| Weird file-lock errors | Project is inside a synced folder (OneDrive). Keep it in a local folder such as `C:\Users\<you>\Projects\`. |

---

*Handoff written at commit `fa72cbc`. Keep this file updated as phases 8 and 9 land.*
