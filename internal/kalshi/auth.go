package kalshi

import (
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"errors"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
)

// Auth header names.
const (
	HeaderKey       = "KALSHI-ACCESS-KEY"
	HeaderSignature = "KALSHI-ACCESS-SIGNATURE"
	HeaderTimestamp = "KALSHI-ACCESS-TIMESTAMP"
)

// Signer produces Kalshi request-signing headers. Every REST request and the
// WebSocket handshake are signed as RSA-PSS-SHA256 over
// "<unix ms timestamp><METHOD><path without query>".
type Signer struct {
	KeyID string
	key   *rsa.PrivateKey
	now   func() time.Time
}

// NewSigner loads an RSA private key from PEM bytes (PKCS#1 or PKCS#8).
func NewSigner(keyID string, pemBytes []byte) (*Signer, error) {
	if keyID == "" {
		return nil, errors.New("kalshi: empty API key id")
	}
	key, err := parsePrivateKey(pemBytes)
	if err != nil {
		return nil, err
	}
	return &Signer{KeyID: keyID, key: key, now: time.Now}, nil
}

// NewSignerFromFile loads the key from a PEM file.
func NewSignerFromFile(keyID, path string) (*Signer, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("kalshi: read private key: %w", err)
	}
	return NewSigner(keyID, b)
}

func parsePrivateKey(pemBytes []byte) (*rsa.PrivateKey, error) {
	block, _ := pem.Decode(pemBytes)
	if block == nil {
		return nil, errors.New("kalshi: no PEM block in private key")
	}
	if k, err := x509.ParsePKCS1PrivateKey(block.Bytes); err == nil {
		return k, nil
	}
	k, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("kalshi: parse private key: %w", err)
	}
	rsaKey, ok := k.(*rsa.PrivateKey)
	if !ok {
		return nil, fmt.Errorf("kalshi: private key is %T, want RSA", k)
	}
	return rsaKey, nil
}

// Sign returns the base64 signature for a timestamp/method/path triple.
func (s *Signer) Sign(timestampMs int64, method, path string) (string, error) {
	path, _, _ = strings.Cut(path, "?")
	msg := strconv.FormatInt(timestampMs, 10) + strings.ToUpper(method) + path
	digest := sha256.Sum256([]byte(msg))
	sig, err := rsa.SignPSS(rand.Reader, s.key, crypto.SHA256, digest[:], &rsa.PSSOptions{
		SaltLength: rsa.PSSSaltLengthEqualsHash,
	})
	if err != nil {
		return "", fmt.Errorf("kalshi: sign: %w", err)
	}
	return base64.StdEncoding.EncodeToString(sig), nil
}

// Headers returns the three auth headers for a request made now.
func (s *Signer) Headers(method, path string) (http.Header, error) {
	ts := s.now().UnixMilli()
	sig, err := s.Sign(ts, method, path)
	if err != nil {
		return nil, err
	}
	h := http.Header{}
	h.Set(HeaderKey, s.KeyID)
	h.Set(HeaderTimestamp, strconv.FormatInt(ts, 10))
	h.Set(HeaderSignature, sig)
	return h, nil
}

// SignRequest adds auth headers to an outgoing HTTP request. Its signature
// matches oapi-codegen's RequestEditorFn.
func (s *Signer) SignRequest(req *http.Request) error {
	h, err := s.Headers(req.Method, req.URL.Path)
	if err != nil {
		return err
	}
	for k, v := range h {
		req.Header[k] = v
	}
	return nil
}

// PublicKey exposes the verifying key (used by tests).
func (s *Signer) PublicKey() *rsa.PublicKey { return &s.key.PublicKey }
