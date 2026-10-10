# ADR 0002: Hugging Face Space for the demo, kind in CI for Kubernetes

- Status: Accepted
- Date: 2026-10-10
- Source: ARCHITECTURE.md (Deployment, Deliberate trade-offs, Known limitations)

## Context
Hosting must be free and card-free. The project also needs evidence that it deploys in a production-style way to Kubernetes, without any cloud account.

## Decision
- **Public demo:** a Hugging Face Space using the Docker SDK. One container runs the API, Prometheus, and Grafana under a process supervisor. Disk is treated as ephemeral: the SQLite file is rebuilt from committed seed fixtures on start. No Docker daemon is assumed inside the Space, so only static validation runs there. The Space port, user, and README metadata requirements must be checked against the current Spaces docs when the Space is built.
- **Kubernetes verification:** a throwaway `kind` cluster inside GitHub Actions (`e2e-kind.yml`). Terraform deploys the app onto it with the Kubernetes or Helm provider (chosen in S10, with its own ADR), runs smoke tests, and destroys the cluster.
- **Terraform scope:** CI only. No cloud credentials and no remote state. State stays on the ephemeral runner and is never committed. Provider versions are pinned and the lock file is committed. `terraform fmt -check`, `terraform validate`, and a Trivy config scan are CI gates.
- GitHub Actions is the primary CI, since it is free for public repositories. The GitHub webhook targets the Space URL, and cold starts are acceptable.

## Consequences
- The Space is a demo host, not a production platform. The Kubernetes manifests and the Terraform-on-kind e2e test are the production-style deployment evidence.
- The demo cannot build images. Build-verified results come from the Actions benchmark (`eval.yml`).
- Cold starts on the Space delay webhook handling and are documented rather than engineered away.
