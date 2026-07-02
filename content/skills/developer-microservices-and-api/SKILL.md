# Microservices and API Design

Contract-first API design and microservices patterns. Covers REST, gRPC, and GraphQL.
Based on [Microsoft Microservices Architecture Guide](https://learn.microsoft.com/en-us/azure/architecture/microservices/), [Google API Design Guide](https://cloud.google.com/apis/design), and key patterns from [microservices.io](https://microservices.io/patterns/index.html).

## Core Principle: Contract First

> Ref: [API-First Design](https://swagger.io/resources/articles/adopting-an-api-first-approach/), [OpenAPI Initiative](https://www.openapis.org/)

Define the interface before writing implementation code. The contract is the primary artifact code is derived from it.

```
Contract (OpenAPI / Protobuf / SDL) → Generate stubs → Implement logic
```

Benefits: clients can work against the contract immediately, breaking changes are visible before deployment, documentation is always accurate.

## REST API Design

> Ref: [Google API Design Guide Resource names](https://cloud.google.com/apis/design/resource_names), [Microsoft REST API Guidelines](https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md), [RFC 9110 HTTP Semantics](https://httpwg.org/specs/rfc9110.html)

### Resource naming

```
# Good nouns, plural, hierarchical
GET    /users
GET    /users/{id}
POST   /users
PUT    /users/{id}
PATCH  /users/{id}
DELETE /users/{id}

GET    /users/{id}/orders
GET    /orders/{id}

# Bad
GET /getUsers
POST /createUser
GET /user_list
```

### Status codes be precise

> Ref: [RFC 9110 Status Codes](https://httpwg.org/specs/rfc9110.html#status.codes), [IANA Status Code Registry](https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml)

| Code | Use                                                    |
| ---- | ------------------------------------------------------ |
| 200  | Success with body                                      |
| 201  | Created include `Location` header                      |
| 204  | Success, no body (DELETE, some PATCHes)                |
| 400  | Client error malformed request, validation failure     |
| 401  | Not authenticated                                      |
| 403  | Authenticated but not authorized                       |
| 404  | Resource not found                                     |
| 409  | Conflict (duplicate, concurrent modification)          |
| 422  | Unprocessable entity valid JSON but semantically wrong |
| 429  | Rate limited include `Retry-After` header              |
| 500  | Server error never expose internals                    |

### Versioning

- URL versioning for breaking changes: `/v1/users`, `/v2/users`
- Header versioning (`Accept: application/vnd.api+json;version=2`) for fine-grained negotiation
- Never version by query parameter
- Deprecation: add `Sunset` and `Deprecation` headers, keep old version alive for 6+ months

### Pagination

> Ref: [Relay Connection Specification](https://relay.dev/graphql/connections.htm), [Google AIP-158 Pagination](https://google.aip.dev/158)

```json
// Cursor-based (preferred for large/live datasets)
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6MTAwfQ==",
    "hasMore": true
  }
}

// Offset-based (acceptable for small stable datasets)
{
  "data": [...],
  "pagination": {
    "page": 2,
    "perPage": 20,
    "total": 143
  }
}
```

### Error response format

Consistent error body across all endpoints:

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Request validation failed",
    "details": [{ "field": "email", "message": "Invalid email format" }]
  }
}
```

## gRPC

> Ref: [gRPC Documentation](https://grpc.io/docs/), [Protocol Buffers Language Guide](https://protobuf.dev/programming-guides/proto3/), [Buf linting & breaking change detection](https://buf.build/docs/)

Use when: low-latency inter-service communication, streaming, strict contracts, polyglot services.

```protobuf
syntax = "proto3";
package user.v1;

service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (stream User);
}

message User {
  string id = 1;
  string name = 2;
  string email = 3;
  google.protobuf.Timestamp created_at = 4;
}
```

**Rules:**

- Always use `google.protobuf.Timestamp` for timestamps, not strings
- Never remove or renumber fields mark deprecated with `[deprecated = true]`
- Use `buf` for linting and breaking change detection
- Version your proto packages: `user.v1`, `user.v2`

## GraphQL

> Ref: [GraphQL Specification](https://spec.graphql.org/), [Apollo Best Practices](https://www.apollographql.com/docs/), [Relay Specification](https://relay.dev/docs/guides/graphql-server-specification/)

Use when: flexible data fetching for client-driven apps, aggregation gateway over multiple services.

```graphql
type Query {
  user(id: ID!): User
  users(filter: UserFilter, first: Int, after: String): UserConnection!
}

type User {
  id: ID!
  name: String!
  orders(first: Int, after: String): OrderConnection!
}
```

**Rules:**

- Use `Connection` pattern (Relay spec) for paginated lists
- Avoid N+1 queries use DataLoader or batching
- Always define input types for mutations (not raw scalars)
- Use persisted queries in production to prevent abuse

## Service Boundaries

> Ref: [Bounded Context Martin Fowler](https://martinfowler.com/bliki/BoundedContext.html), [Decompose by business capability](https://microservices.io/patterns/decomposition/decompose-by-business-capability.html), [Database per service](https://microservices.io/patterns/data/database-per-service.html)

```
Correct: one service owns one bounded context
Bad: service A calls service B calls service C (synchronous chain)
```

**Communication patterns:**

| Pattern                  | Use when                                            | Reference                                                                               |
| ------------------------ | --------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Synchronous REST/gRPC    | Response needed immediately, simple request-reply   | [Request/Reply](https://microservices.io/patterns/communication-style/messaging.html)   |
| Async events (Kafka/SQS) | Fire-and-forget, eventual consistency acceptable    | [Async Messaging](https://microservices.io/patterns/communication-style/messaging.html) |
| Saga pattern             | Distributed transactions across services            | [Saga Pattern](https://microservices.io/patterns/data/saga.html)                        |
| CQRS                     | Separate read/write models, different scaling needs | [CQRS Pattern](https://microservices.io/patterns/data/cqrs.html)                        |
| Event Sourcing           | Full audit trail, temporal queries, complex domain  | [Event Sourcing](https://microservices.io/patterns/data/event-sourcing.html)            |

**Rules:**

- Services communicate via APIs or events never via shared databases
- Each service owns its data store ([Database per Service](https://microservices.io/patterns/data/database-per-service.html))
- Design for failure: circuit breakers, retries with exponential backoff, timeouts
- Use idempotency keys for POST/PUT operations that must not be duplicated

## Resilience Patterns

> Ref: [Circuit Breaker Martin Fowler](https://martinfowler.com/bliki/CircuitBreaker.html), [Retry pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/retry), [Bulkhead pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead)

Distributed systems fail partially. Design every service interaction assuming the other side can be slow, broken, or unreachable.

| Pattern                | Purpose                                      | When to use                                       |
| ---------------------- | -------------------------------------------- | ------------------------------------------------- |
| **Circuit Breaker**    | Stop calling a failing dependency, fail fast | Remote calls that can timeout or error repeatedly |
| **Retry with backoff** | Recover from transient failures              | Network blips, temporary unavailability           |
| **Bulkhead**           | Isolate failures, prevent cascade            | Shared thread pools, connection pools             |
| **Timeout**            | Bound waiting time for external calls        | Every synchronous inter-service call              |
| **Fallback**           | Degrade gracefully instead of failing        | Non-critical features, cached responses           |
| **Rate Limiter**       | Protect services from overload               | Public APIs, shared internal services             |

**Rules:**

- Every outbound HTTP/gRPC call must have a timeout no call should wait indefinitely
- Retry only on transient errors (5xx, timeout, connection reset) retrying on 4xx is a bug
- Use exponential backoff with jitter prevents [thundering herd](https://en.wikipedia.org/wiki/Thundering_herd_problem) on recovery
- Circuit breaker states: Closed → Open (after N failures) → Half-Open (test one request) → Closed
- Combine patterns: timeout + retry + circuit breaker is the standard stack for synchronous calls
- Set bulkhead limits per dependency a slow inventory service must not exhaust the connection pool used by the payment service

## Observability

> Ref: [OpenTelemetry](https://opentelemetry.io/docs/), [Distributed Tracing](https://microservices.io/patterns/observability/distributed-tracing.html), [Health Check API](https://microservices.io/patterns/observability/health-check-api.html)

Without observability, debugging a distributed system is guesswork. The three pillars:

| Pillar      | What it captures                                          | Key standard                                                                                                                 |
| ----------- | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Logs**    | Discrete events (errors, state changes)                   | Structured JSON, correlation IDs                                                                                             |
| **Metrics** | Aggregated measurements (latency, throughput, error rate) | [RED method](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/) Rate, Errors, Duration |
| **Traces**  | Request flow across services                              | [W3C Trace Context](https://www.w3.org/TR/trace-context/), OpenTelemetry                                                     |

**Rules:**

- Propagate trace context (`traceparent` header) across all service calls this is what makes distributed tracing work
- Every service must expose a health check endpoint (`/health` or `/healthz`) that reports dependency status
- Use structured logging (JSON) with `traceId`, `spanId`, `service`, `level` fields not plain text
- Track the four golden signals: latency, traffic, errors, saturation ([Google SRE Book](https://sre.google/sre-book/monitoring-distributed-systems/))
- Set alerts on SLO burn rate, not on raw thresholds avoids noise

## API Security

> Ref: [OWASP API Security Top 10](https://owasp.org/API-Security/), [OAuth 2.0 (RFC 6749)](https://datatracker.ietf.org/doc/html/rfc6749), [JWT Best Practices (RFC 8725)](https://datatracker.ietf.org/doc/html/rfc8725)

**Authentication & Authorization:**

- Use OAuth 2.0 / OpenID Connect for authentication don't invent token schemes
- JWTs for stateless auth between services validate signature, issuer, audience, and expiration on every request
- API keys for machine-to-machine identification but API keys alone are not sufficient for authorization
- Use scopes or RBAC to enforce least-privilege access per endpoint

**Input & Transport:**

- Validate all input at the API boundary type, length, format, range. Never trust client data
- Always use TLS no exceptions, including internal service-to-service communication
- Rate limit and throttle by client/IP return `429` with `Retry-After` header
- Set response headers: `Content-Type`, `X-Content-Type-Options: nosniff`, `Cache-Control` as appropriate

**Data exposure:**

- Never expose internal IDs, stack traces, or database errors in API responses
- Use field-level filtering don't return full objects when the client needs three fields
- Log authentication failures and unusual patterns they signal attacks
- Implement request size limits prevents abuse via oversized payloads

## OpenAPI Specification

> Ref: [OpenAPI 3.1 Specification](https://spec.openapis.org/oas/v3.1.0), [Swagger Editor](https://editor.swagger.io/)

```yaml
openapi: 3.1.0
info:
  title: User API
  version: 1.0.0

paths:
  /users/{id}:
    get:
      operationId: getUser
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        '404':
          $ref: '#/components/responses/NotFound'
```

- Use `$ref` for reusable schemas and responses
- Always define `operationId` enables client generation
- Use `format` for semantic types: `uuid`, `date-time`, `email`

## Design Patterns Quick Reference

> Ref: [microservices.io Patterns](https://microservices.io/patterns/index.html), [Azure Architecture Patterns](https://learn.microsoft.com/en-us/azure/architecture/patterns/)

| Category          | Pattern                                                                                                                   | Problem it solves                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| **Decomposition** | [Decompose by business capability](https://microservices.io/patterns/decomposition/decompose-by-business-capability.html) | How to split a monolith into services   |
| **Decomposition** | [Strangler Fig](https://microservices.io/patterns/refactoring/strangler-application.html)                                 | Incremental migration from monolith     |
| **Data**          | [Database per Service](https://microservices.io/patterns/data/database-per-service.html)                                  | Data isolation between services         |
| **Data**          | [Saga](https://microservices.io/patterns/data/saga.html)                                                                  | Distributed transactions without 2PC    |
| **Data**          | [CQRS](https://microservices.io/patterns/data/cqrs.html)                                                                  | Separate read/write optimization        |
| **Data**          | [Event Sourcing](https://microservices.io/patterns/data/event-sourcing.html)                                              | Audit trail + temporal queries          |
| **Communication** | [API Gateway](https://microservices.io/patterns/apigateway.html)                                                          | Single entry point for clients          |
| **Communication** | [BFF (Backend for Frontend)](https://microservices.io/patterns/apigateway.html)                                           | Per-client optimized API                |
| **Reliability**   | [Circuit Breaker](https://microservices.io/patterns/reliability/circuit-breaker.html)                                     | Stop cascading failures                 |
| **Reliability**   | [Bulkhead](https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead)                                        | Isolate failure domains                 |
| **Observability** | [Distributed Tracing](https://microservices.io/patterns/observability/distributed-tracing.html)                           | Follow requests across services         |
| **Observability** | [Health Check API](https://microservices.io/patterns/observability/health-check-api.html)                                 | Service health monitoring               |
| **Deployment**    | [Sidecar](https://learn.microsoft.com/en-us/azure/architecture/patterns/sidecar)                                          | Cross-cutting concerns (logging, proxy) |
| **Deployment**    | [Service Mesh](https://microservices.io/patterns/deployment/service-mesh.html)                                            | Network-level resilience + security     |

## Anti-Patterns to Flag

### API anti-patterns

- Chatty APIs many small calls instead of one composed call. Use [API Composition](https://microservices.io/patterns/data/api-composition.html) or BFF instead
- Returning 200 for errors with error details in the body use proper HTTP status codes
- Using PUT where PATCH is more appropriate PUT replaces the full resource, PATCH updates fields
- No rate limiting on public endpoints every public API needs throttling
- Missing idempotency on mutation endpoints POST/PUT without idempotency keys cause duplicates on retry
- CRUD-only API design REST resources don't have to map 1:1 to database tables; model business operations
- No pagination on list endpoints unbounded responses kill clients and servers alike

### Architecture anti-patterns

- **Distributed monolith** services that must be deployed together, share databases, or have tight synchronous coupling. If you can't deploy independently, it's not a microservice ([Distributed Monolith](https://www.microservices.com/talks/dont-build-a-distributed-monolith/))
- **Shared database** two services reading/writing the same tables destroys independent deployability and data ownership
- **Synchronous chain** service A → B → C → D. Latency compounds, any failure breaks the chain. Use async events for non-blocking flows
- **Business logic in the API gateway** gateways handle routing, auth, rate limiting. Business rules belong in services
- **Nano-services** services so small they add network overhead without meaningful boundaries. Each service should own a coherent bounded context
- **No contract testing** deploying services without verifying their contracts match consumers leads to integration failures. Use [Consumer-Driven Contract Testing](https://martinfowler.com/articles/consumerDrivenContracts.html) (Pact, etc.)
- **Ignoring eventual consistency** designing as if distributed data is immediately consistent. Use sagas, compensating transactions, and communicate consistency guarantees to clients
- **Missing correlation IDs** without trace propagation, debugging cross-service failures is impossible

## Self-Check

Before finalizing an API or service design, verify against this checklist:

### API Design

- [ ] Contract defined first (OpenAPI / Protobuf / GraphQL SDL) before implementation
- [ ] Resources are nouns, plural, with consistent hierarchical naming
- [ ] HTTP methods and status codes are semantically correct
- [ ] Pagination implemented on all list endpoints (cursor-based preferred)
- [ ] Error responses follow a consistent format with machine-readable codes
- [ ] Versioning strategy defined (URL or header) with deprecation policy
- [ ] `operationId` defined for every endpoint (enables client generation)
- [ ] Input validation at every API boundary type, length, format, range

### Service Architecture

- [ ] Each service owns exactly one bounded context and its data store
- [ ] Services can be deployed, scaled, and rolled back independently
- [ ] No shared database between services
- [ ] Communication is via APIs or events no hidden coupling
- [ ] Async messaging used for fire-and-forget operations (not synchronous calls)

### Resilience

- [ ] Every outbound call has a timeout
- [ ] Retries use exponential backoff with jitter, only on transient errors
- [ ] Circuit breakers protect against cascading failures from slow/broken dependencies
- [ ] Idempotency keys on all mutation endpoints
- [ ] Graceful degradation defined what happens when a dependency is down?

### Observability

- [ ] Structured logging with correlation/trace IDs propagated across services
- [ ] Health check endpoint exposed (`/health` or `/healthz`)
- [ ] Metrics collected: latency (p50/p95/p99), error rate, throughput
- [ ] Distributed tracing enabled (OpenTelemetry or equivalent)
- [ ] Alerts based on SLO burn rate, not raw thresholds

### Security

- [ ] Authentication via OAuth 2.0 / OIDC not custom token schemes
- [ ] Authorization enforced per endpoint (scopes or RBAC)
- [ ] TLS everywhere including internal service-to-service traffic
- [ ] Rate limiting on public and shared internal endpoints
- [ ] No internal IDs, stack traces, or DB errors exposed in responses
- [ ] Request size limits configured

## Reference Links

| Topic                          | Link                                                                |
| ------------------------------ | ------------------------------------------------------------------- |
| Microsoft Microservices Guide  | https://learn.microsoft.com/en-us/azure/architecture/microservices/ |
| Google API Design Guide        | https://cloud.google.com/apis/design                                |
| microservices.io Patterns      | https://microservices.io/patterns/index.html                        |
| OpenAPI 3.1 Specification      | https://spec.openapis.org/oas/v3.1.0                                |
| gRPC Documentation             | https://grpc.io/docs/                                               |
| Protocol Buffers Guide         | https://protobuf.dev/programming-guides/proto3/                     |
| GraphQL Specification          | https://spec.graphql.org/                                           |
| RFC 9110 HTTP Semantics        | https://httpwg.org/specs/rfc9110.html                               |
| RFC 6749 OAuth 2.0             | https://datatracker.ietf.org/doc/html/rfc6749                       |
| RFC 8725 JWT Best Practices    | https://datatracker.ietf.org/doc/html/rfc8725                       |
| OWASP API Security Top 10      | https://owasp.org/API-Security/                                     |
| OpenTelemetry                  | https://opentelemetry.io/docs/                                      |
| W3C Trace Context              | https://www.w3.org/TR/trace-context/                                |
| Google SRE Book Monitoring     | https://sre.google/sre-book/monitoring-distributed-systems/         |
| Relay Connection Specification | https://relay.dev/graphql/connections.htm                           |
| Martin Fowler Circuit Breaker  | https://martinfowler.com/bliki/CircuitBreaker.html                  |
| Azure Architecture Patterns    | https://learn.microsoft.com/en-us/azure/architecture/patterns/      |
