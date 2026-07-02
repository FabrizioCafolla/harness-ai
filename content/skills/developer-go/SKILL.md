# Go Conventions

Idiomatic Go standards. Assumes basic syntax knowledge this covers non-obvious decisions and common Go-specific patterns.
Based on [Effective Go](https://go.dev/doc/effective_go), [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments), and [Go Proverbs](https://go-proverbs.github.io/).

## Tooling

> Ref: [Go Tools](https://pkg.go.dev/cmd), [golangci-lint](https://golangci-lint.run/)

- **Format**: `gofmt` / `goimports` (non-negotiable enforced in CI)
- **Lint**: `golangci-lint` with at minimum `errcheck`, `staticcheck`, `govet`, `gosimple`
- **Test**: `go test ./...` no external test framework needed
- **Deps**: Go modules (`go.mod`) pin major versions, use `go mod tidy` in CI
- **Build**: `go build` with `-ldflags="-s -w"` for production binaries

## Project Structure

> Ref: [Go Project Layout](https://go.dev/doc/modules/layout), [internal packages](https://go.dev/doc/go1.4#internalpackages)

```
myapp/
├── cmd/
│   └── myapp/
│       └── main.go        # Entrypoint thin, wires dependencies
├── internal/              # Private packages not importable externally
│   ├── handler/
│   ├── service/
│   └── repository/
├── pkg/                   # Public reusable packages (only if lib-worthy)
├── config/
├── go.mod
└── go.sum
```

- `cmd/` for entrypoints one subdirectory per binary
- `internal/` for application logic prevents accidental external use
- Flat package structure is fine for small projects; avoid deep nesting

## Error Handling

> Ref: [Error handling and Go](https://go.dev/blog/error-handling-and-go), [Working with Errors in Go 1.13](https://go.dev/blog/go1.13-errors)

Go errors are values handle them explicitly, every time.

```go
// Good wrap with context
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}

// Checking error types
var notFound *NotFoundError
if errors.As(err, &notFound) {
    // handle specific error
}

// Checking sentinel errors
if errors.Is(err, sql.ErrNoRows) {
    // handle no rows
}
```

**Rules:**

- Always check returned errors never `_` an error unless it is genuinely impossible
- Use `%w` in `fmt.Errorf` to wrap errors (enables `errors.Is` / `errors.As` unwrapping)
- Use `errors.As` for type-checking, `errors.Is` for sentinel values
- Define custom error types when callers need to branch on error kind

## Interfaces

> Ref: [Effective Go Interfaces](https://go.dev/doc/effective_go#interfaces), [Go Wiki Accept interfaces, return structs](https://go.dev/wiki/CodeReviewComments#interfaces)

```go
// Good define interfaces where they are consumed, not where they are implemented
// (consumer-side interfaces enable decoupling without explicit registration)

// In the service package, define what it needs
type UserStore interface {
    FindByID(ctx context.Context, id string) (*User, error)
}

// The database package implements it without knowing about this interface
```

**Rules:**

- Keep interfaces small 1-3 methods is ideal (interface segregation)
- Don't return concrete types from constructors when interfaces enable testing
- Accept interfaces, return concrete types (or errors)

## Concurrency

> Ref: [Effective Go Concurrency](https://go.dev/doc/effective_go#concurrency), [Go Concurrency Patterns](https://go.dev/blog/pipelines), [Context](https://pkg.go.dev/context)

```go
// Always pass context for cancellation
func fetchData(ctx context.Context, url string) ([]byte, error) {
    req, _ := http.NewRequestWithContext(ctx, "GET", url, nil)
    // ...
}

// Use sync.WaitGroup for fan-out
var wg sync.WaitGroup
for _, item := range items {
    wg.Add(1)
    go func(item Item) {
        defer wg.Done()
        process(item)
    }(item)
}
wg.Wait()

// Prefer channels over shared memory + mutex when passing data between goroutines
results := make(chan Result, len(items))
```

**Rules:**

- Never start a goroutine without a way to stop it (context cancellation or channel close)
- Use `sync.Mutex` for protecting shared state, `sync/atomic` for simple counters
- `defer` unlock immediately after lock to prevent forgetting
- Close channels from the sender, never the receiver

## Testing

> Ref: [Testing package](https://pkg.go.dev/testing), [Table-driven tests](https://go.dev/wiki/TableDrivenTests)

```go
// Table-driven tests the Go standard
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
        {"zero", 0, 0, 0},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := Add(tt.a, tt.b)
            if got != tt.expected {
                t.Errorf("Add(%d, %d) = %d, want %d", tt.a, tt.b, got, tt.expected)
            }
        })
    }
}
```

- Use `t.Helper()` in test utility functions
- Use `t.Cleanup()` instead of `defer` in tests (runs even if subtests fail)
- Use interfaces to inject test doubles avoid global state in production code
- `testify/assert` is acceptable but not required; prefer stdlib when it's readable

## Naming

| Pattern        | Convention                                                        |
| -------------- | ----------------------------------------------------------------- |
| Packages       | Short, lowercase, no underscores: `http`, `user`, `config`        |
| Exported types | PascalCase: `UserService`, `Config`                               |
| Unexported     | camelCase: `parseConfig`, `maxRetries`                            |
| Acronyms       | Consistent case: `URL`, `HTTP`, `userID`, `httpClient`            |
| Receivers      | Short abbreviation of type: `func (u *User)`, `func (s *Service)` |
| Error types    | Suffix with `Error`: `ValidationError`, `NotFoundError`           |

## Anti-Patterns to Flag

- `init()` functions with side effects makes startup order unpredictable and testing harder; prefer explicit initialization in `main()`
- Global variables for dependencies creates hidden coupling; inject via constructors for testability
- Returning `interface{}` (or `any`) instead of concrete types forces callers into type assertions; return concrete, accept interfaces
- Ignoring `context.Context` in long-running or I/O operations prevents cancellation and timeout propagation
- Using `panic` for recoverable errors `panic` is for programmer errors (bugs), not operational failures; return errors instead
- Named return values without clear benefit increases cognitive load; use only when it genuinely improves readability (e.g., multiple returns of same type)
- Deep embedding instead of composition embed for behavior promotion only, not to inherit fields; prefer explicit delegation
- Unbuffered channels used as queues causes goroutine leaks when receiver isn't ready; size the buffer or use `sync` primitives
- `go func()` without error collection silently discards errors from goroutines; use `errgroup.Group` for concurrent error propagation

## Self-Check

- [ ] Every returned `error` is checked no `_` on error values
- [ ] Errors wrapped with `%w` and context message (`fmt.Errorf("doing X: %w", err)`)
- [ ] Interfaces defined at consumer side, not implementor side
- [ ] Every goroutine has a cancellation path (context or channel close)
- [ ] `defer` used immediately after acquiring a resource (lock, file, connection)
- [ ] Table-driven tests for functions with multiple input cases
- [ ] `golangci-lint` passes in CI with `errcheck`, `staticcheck`, `govet`
- [ ] No `init()` with side effects explicit setup in `main()`
- [ ] `internal/` used for packages that should not be imported externally
