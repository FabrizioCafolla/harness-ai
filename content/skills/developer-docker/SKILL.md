# Docker and Container Conventions

Best practices for Dockerfiles, Compose files, and containerized applications.
Based on [Docker official documentation](https://docs.docker.com/) and [Dockerfile best practices](https://docs.docker.com/build/building/best-practices/).

## Dockerfile Principles

### Multi-stage builds always for production

> Ref: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)

```dockerfile
# Stage 1: build
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --frozen-lockfile
COPY . .
RUN npm run build

# Stage 2: runtime only what's needed
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json .
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

**Rules:**

- Separate build and runtime stages never ship build tools in the final image
- Use `AS` stage names reference them explicitly
- Run as non-root user always create and switch to a dedicated app user
- Use `npm ci` not `npm install` reproducible installs with lockfile enforcement

### BuildKit features use them

> Ref: [BuildKit](https://docs.docker.com/build/buildkit/), [Dockerfile frontend syntax](https://docs.docker.com/build/buildkit/dockerfile-frontend/)

BuildKit is the default builder since Docker 23.0. Use its features:

```dockerfile
# syntax=docker/dockerfile:1

# Cache package manager downloads across builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Mount secrets without baking them into layers
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm ci --frozen-lockfile

# Bind-mount files from another stage without COPY
RUN --mount=type=bind,from=builder,source=/app/dist,target=/tmp/dist \
    cp -r /tmp/dist ./dist
```

**Rules:**

- Add `# syntax=docker/dockerfile:1` at the top of the Dockerfile enables latest stable features
- Use `--mount=type=cache` for package manager caches (`pip`, `npm`, `apt`) avoids re-downloading on every build
- Use `--mount=type=secret` for credentials needed at build time never use `ARG` or `ENV` for secrets, they persist in image layers
- See [Build secrets](https://docs.docker.com/build/building/secrets/) for passing secrets at build time

### Layer caching order matters

> Ref: [Optimize cache usage](https://docs.docker.com/build/cache/optimize/)

```dockerfile
# Good dependencies before source code
COPY package*.json ./
RUN npm ci
COPY . .          # Changes here don't invalidate the npm ci layer

# Bad any source change invalidates the npm ci layer
COPY . .
RUN npm ci
```

**Rule**: Copy dependency manifests first, install dependencies, then copy source. This maximizes cache hits.

### Base images

> Ref: [Docker Official Images](https://hub.docker.com/search?image_filter=official), [Distroless](https://github.com/GoogleContainerTools/distroless)

| Use case      | Image                                                                         |
| ------------- | ----------------------------------------------------------------------------- |
| Node.js       | `node:22-alpine`                                                              |
| Python        | `python:3.13-slim`                                                            |
| Go            | Build on `golang:1.23-alpine`, run on `gcr.io/distroless/static` or `scratch` |
| Java          | `eclipse-temurin:21-jre-alpine`                                               |
| Generic Linux | `debian:bookworm-slim` or `alpine:3.21`                                       |

- Prefer `alpine` or `slim` variants significantly smaller attack surface
- Pin to minor versions (`node:22-alpine`) not `latest` reproducibility
- Use `distroless` or `scratch` for Go/Rust binaries when possible

### Security hardening

> Ref: [Docker security](https://docs.docker.com/engine/security/), [Dockerfile security best practices](https://docs.docker.com/build/building/best-practices/#security)

```dockerfile
# Remove package manager cache
RUN apk add --no-cache curl

# Don't install SSH, sudo, or other unnecessary tools in runtime images
# Use COPY --chown instead of RUN chown (fewer layers)
COPY --chown=appuser:appgroup dist/ ./dist/

# Read-only filesystem where possible
# Set via docker run --read-only or compose security_opt
```

## Docker Compose

> Ref: [Compose specification](https://docs.docker.com/compose/compose-file/), [Compose file reference](https://docs.docker.com/reference/compose-file/)

```yaml
services:
  app:
    build:
      context: .
      target: runtime # Reference specific multi-stage target
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL} # Never hardcode secrets in compose
    ports:
      - '3000:3000'
    depends_on:
      db:
        condition: service_healthy # Wait for health check, not just start
    restart: unless-stopped
    networks:
      - internal

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U postgres']
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - internal

volumes:
  db-data:

networks:
  internal: # Internal network not exposed to host
```

**Rules:**

- Use `depends_on.condition: service_healthy` not just `depends_on: db` ([Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/))
- Use named volumes for persistent data anonymous volumes are lost on `docker compose down` ([Volumes in Compose](https://docs.docker.com/compose/how-tos/volumes/))
- Use networks to isolate services don't expose DB ports to the host ([Compose networking](https://docs.docker.com/compose/how-tos/networking/))
- Put secrets in `.env` file (gitignored) reference with `${VAR}`, never hardcode ([Environment variables in Compose](https://docs.docker.com/compose/how-tos/environment-variables/))
- Use [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/) to selectively enable services for different environments (dev, test, debug)

## .dockerignore

> Ref: [.dockerignore file](https://docs.docker.com/build/building/context/#dockerignore-files)

Always create `.dockerignore` it works like `.gitignore` for build context:

```
.git
node_modules
.env
.env.*
dist
*.log
coverage
.DS_Store
Dockerfile*
docker-compose*
README.md
```

Omitting this sends the entire project (including `node_modules`) as build context slow and potentially insecure.

## Container Security

Security is not a single layer it spans build time, image content, runtime configuration, and supply chain. Each stage has its own controls.

### Build-time security

> Ref: [Build secrets](https://docs.docker.com/build/building/secrets/), [Dockerfile best practices security](https://docs.docker.com/build/building/best-practices/#security)

```dockerfile
# syntax=docker/dockerfile:1

# Never pass secrets as ARG they're visible in image history
# BAD:
ARG DB_PASSWORD
RUN echo "$DB_PASSWORD" > /app/.env

# GOOD mount secret at build time, never persisted in layers
RUN --mount=type=secret,id=db_password \
    cat /run/secrets/db_password > /tmp/db_password && \
    ./setup-db.sh /tmp/db_password && \
    rm /tmp/db_password
```

```bash
# Pass secret at build time:
docker build --secret id=db_password,src=./secrets/db_password.txt .
```

**Rules:**

- Never use `ARG` or `ENV` for sensitive data both are visible via `docker history` and `docker inspect`
- Use `--mount=type=secret` for any credential needed at build time
- If you must use `.env` files, ensure they're in `.dockerignore` and `.gitignore`
- Avoid installing packages from untrusted sources in `RUN` instructions

### Image scanning and supply chain

> Ref: [Docker Scout](https://docs.docker.com/scout/), [Docker Scout quickstart](https://docs.docker.com/scout/quickstart/), [Provenance attestations](https://docs.docker.com/build/attestations/slsa-provenance/)

```bash
# Scan image for known vulnerabilities (CVEs)
docker scout cves myapp:latest

# Quick overview of image health
docker scout quickview myapp:latest

# Compare vulnerabilities between two versions
docker scout compare myapp:latest --to myapp:previous
```

**Rules:**

- Scan images in CI before pushing to registry fail the pipeline on critical/high CVEs
- Rebuild images regularly to pick up base image security patches don't let images age
- Use [SBOM attestations](https://docs.docker.com/build/attestations/sbom/) to track what's inside images
- Pin base image digests in production for full reproducibility: `FROM node:22-alpine@sha256:abc123...`
- Audit `RUN curl | sh` patterns prefer package managers with verified sources

### Runtime security

> Ref: [Docker security](https://docs.docker.com/engine/security/), [Rootless mode](https://docs.docker.com/engine/security/rootless/), [AppArmor](https://docs.docker.com/engine/security/apparmor/), [Seccomp](https://docs.docker.com/engine/security/seccomp/)

```bash
# Run container as non-root, read-only filesystem, drop all capabilities
docker run \
  --user 1000:1000 \
  --read-only \
  --tmpfs /tmp \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --security-opt no-new-privileges:true \
  myapp:latest
```

**Rules:**

- Drop all Linux capabilities with `--cap-drop ALL`, add back only what's needed principle of least privilege
- Use `--security-opt no-new-privileges:true` prevents processes from gaining additional privileges via setuid/setgid
- Use `--read-only` with `--tmpfs` for temporary directories prevents filesystem tampering at runtime
- Never run containers with `--privileged` in production it disables all security boundaries
- Limit resources with `--memory`, `--cpus`, `--pids-limit` prevents resource exhaustion attacks
- Use [user namespaces](https://docs.docker.com/engine/security/userns-remap/) or [rootless mode](https://docs.docker.com/engine/security/rootless/) on the host for defense in depth

### Compose security configuration

> Ref: [Compose deploy resources](https://docs.docker.com/reference/compose-file/deploy/), [Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/)

```yaml
services:
  app:
    image: myapp:latest
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '1.0'
          pids: 100
    secrets:
      - db_password
    user: '1000:1000'

secrets:
  db_password:
    file: ./secrets/db_password.txt # File-based secret, not in environment
```

**Rules:**

- Use Compose `secrets` instead of environment variables for sensitive data environment variables are visible in `docker inspect` and process listings
- Set resource limits (`memory`, `cpus`, `pids`) prevents a single container from exhausting the host
- Apply `read_only`, `cap_drop`, `security_opt` at service level same runtime hardening as `docker run` flags
- Use `user:` to run as non-root even if the image's `USER` instruction is missing

### Security checklist

- [ ] No secrets in `ARG`, `ENV`, or baked into layers use `--mount=type=secret` or Compose `secrets`
- [ ] Non-root user in Dockerfile (`USER`) and at runtime (`user:`)
- [ ] All capabilities dropped, only required ones re-added
- [ ] `no-new-privileges` security option enabled
- [ ] Read-only root filesystem with `tmpfs` for writeable paths
- [ ] Base images from trusted sources (Docker Official Images, verified publishers)
- [ ] Image scanning in CI pipeline (Docker Scout, Trivy, or Grype)
- [ ] Resource limits set (memory, CPU, PIDs)
- [ ] No `--privileged` flag in production
- [ ] Regular image rebuilds to pick up base image patches
- [ ] Network segmentation services only on networks they need

## Image Optimization Checklist

- [ ] Multi-stage build (build tools not in runtime image)
- [ ] `alpine` or `slim` base image
- [ ] `--no-cache` for package managers in Alpine (`apk add --no-cache`)
- [ ] Dependency manifests copied before source code
- [ ] Non-root user created and used
- [ ] `.dockerignore` present and comprehensive
- [ ] No secrets or credentials in any layer
- [ ] Explicit version tags (no `latest`)
- [ ] `HEALTHCHECK` instruction for production images

## Anti-Patterns to Flag

- `RUN apt-get install` without `rm -rf /var/lib/apt/lists/*` bloats image
- Hardcoded secrets in `ENV` or `ARG` instructions use `--mount=type=secret` instead
- Running as root in the final image
- `CMD ["bash"]` or `ENTRYPOINT ["/bin/sh"]` as the main process (not for apps)
- Copying entire project before installing dependencies
- Using `:latest` tag in production Dockerfiles
- Multiple `RUN` commands that could be chained with `&&`
- Missing `# syntax=docker/dockerfile:1` directive prevents access to BuildKit features
- Using `ADD` when `COPY` suffices `ADD` has implicit behaviors (tar extraction, URL fetching) that can surprise

## Official Documentation Quick Reference

| Topic                                 | Link                                                           |
| ------------------------------------- | -------------------------------------------------------------- |
| Dockerfile reference                  | https://docs.docker.com/reference/dockerfile/                  |
| Build best practices                  | https://docs.docker.com/build/building/best-practices/         |
| Multi-stage builds                    | https://docs.docker.com/build/building/multi-stage/            |
| BuildKit                              | https://docs.docker.com/build/buildkit/                        |
| Build secrets                         | https://docs.docker.com/build/building/secrets/                |
| Build cache                           | https://docs.docker.com/build/cache/                           |
| Compose file reference                | https://docs.docker.com/reference/compose-file/                |
| Compose networking                    | https://docs.docker.com/compose/how-tos/networking/            |
| Compose environment variables         | https://docs.docker.com/compose/how-tos/environment-variables/ |
| Docker security                       | https://docs.docker.com/engine/security/                       |
| Rootless mode                         | https://docs.docker.com/engine/security/rootless/              |
| AppArmor profiles                     | https://docs.docker.com/engine/security/apparmor/              |
| Seccomp profiles                      | https://docs.docker.com/engine/security/seccomp/               |
| Compose secrets                       | https://docs.docker.com/compose/how-tos/use-secrets/           |
| SBOM attestations                     | https://docs.docker.com/build/attestations/sbom/               |
| Docker Init                           | https://docs.docker.com/reference/cli/docker/init/             |
| Docker Scout (vulnerability scanning) | https://docs.docker.com/scout/                                 |
