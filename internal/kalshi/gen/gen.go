// Package gen holds the REST client and types generated from specs/openapi.yaml.
//
// Regenerate with `go generate ./...` after refreshing the spec (make specs).
package gen

//go:generate go tool oapi-codegen -config oapi-codegen.yaml ../../../specs/openapi.yaml
