package kalshi

import "fmt"

// Env selects the production or demo exchange.
type Env string

const (
	Prod Env = "prod"
	Demo Env = "demo"
)

// WSPath is the WebSocket path; it is also the path signed for the handshake.
const WSPath = "/trade-api/ws/v2"

// ParseEnv accepts "prod" or "demo".
func ParseEnv(s string) (Env, error) {
	switch Env(s) {
	case Prod, Demo:
		return Env(s), nil
	}
	return "", fmt.Errorf("kalshi: unknown env %q (want prod or demo)", s)
}

// wsOverride lets tests point an Env at a local server.
var wsOverride = map[Env]string{}

// SetWSURLForTest overrides the WebSocket URL for env and returns a restore func.
func SetWSURLForTest(env Env, url string) func() {
	prev := wsOverride[env]
	wsOverride[env] = url
	return func() { wsOverride[env] = prev }
}

// RESTBase is the base URL for REST calls, including the /trade-api/v2 prefix.
func (e Env) RESTBase() string {
	if e == Demo {
		return "https://external-api.demo.kalshi.co/trade-api/v2"
	}
	return "https://external-api.kalshi.com/trade-api/v2"
}

// WSURL is the WebSocket endpoint.
func (e Env) WSURL() string {
	if u := wsOverride[e]; u != "" {
		return u
	}
	if e == Demo {
		return "wss://external-api-ws.demo.kalshi.co" + WSPath
	}
	return "wss://external-api-ws.kalshi.com" + WSPath
}
