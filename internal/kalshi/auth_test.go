package kalshi

import (
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/pem"
	"net/http"
	"testing"
	"time"
)

func testKeyPEM(t *testing.T, pkcs8 bool) []byte {
	t.Helper()
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal(err)
	}
	if pkcs8 {
		der, err := x509.MarshalPKCS8PrivateKey(key)
		if err != nil {
			t.Fatal(err)
		}
		return pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: der})
	}
	return pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: x509.MarshalPKCS1PrivateKey(key)})
}

func TestSignerVerifies(t *testing.T) {
	for _, pkcs8 := range []bool{false, true} {
		s, err := NewSigner("kid", testKeyPEM(t, pkcs8))
		if err != nil {
			t.Fatal(err)
		}
		s.now = func() time.Time { return time.UnixMilli(1669149841000) }

		// Query string must not be part of the signed message.
		h, err := s.Headers("get", "/trade-api/v2/markets?limit=5")
		if err != nil {
			t.Fatal(err)
		}
		if h.Get(HeaderKey) != "kid" || h.Get(HeaderTimestamp) != "1669149841000" {
			t.Errorf("headers = %v", h)
		}
		sig, err := base64.StdEncoding.DecodeString(h.Get(HeaderSignature))
		if err != nil {
			t.Fatal(err)
		}
		digest := sha256.Sum256([]byte("1669149841000GET/trade-api/v2/markets"))
		err = rsa.VerifyPSS(s.PublicKey(), crypto.SHA256, digest[:], sig, &rsa.PSSOptions{SaltLength: rsa.PSSSaltLengthEqualsHash})
		if err != nil {
			t.Errorf("pkcs8=%v: signature does not verify: %v", pkcs8, err)
		}
	}
}

func TestSignRequest(t *testing.T) {
	s, err := NewSigner("kid", testKeyPEM(t, false))
	if err != nil {
		t.Fatal(err)
	}
	req, _ := http.NewRequestWithContext(context.Background(), "GET", "https://example.com/trade-api/v2/markets/X/orderbook?depth=3", nil)
	if err := s.SignRequest(req); err != nil {
		t.Fatal(err)
	}
	for _, h := range []string{HeaderKey, HeaderTimestamp, HeaderSignature} {
		if req.Header.Get(h) == "" {
			t.Errorf("missing header %s", h)
		}
	}
}

func TestBadKey(t *testing.T) {
	if _, err := NewSigner("kid", []byte("not a pem")); err == nil {
		t.Error("expected error for bad PEM")
	}
	if _, err := NewSigner("", testKeyPEM(t, false)); err == nil {
		t.Error("expected error for empty key id")
	}
}
