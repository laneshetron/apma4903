// Package config loads the collector's YAML config and credentials from env.
package config

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/laneshetron/kalshi/internal/kalshi"
)

// Config is the on-disk YAML shape.
type Config struct {
	Env     string `yaml:"env"`
	Markets struct {
		Tickers         []string      `yaml:"tickers"`
		Series          []string      `yaml:"series"`
		RefreshInterval time.Duration `yaml:"refresh_interval"`
		// AllMinVolume24h > 0 records every open market on the exchange whose
		// 24 h volume is at least this many contracts (listed via /events with
		// nested markets), in addition to Tickers and Series.
		AllMinVolume24h float64  `yaml:"all_min_volume_24h"`
		ExcludeSeries   []string `yaml:"exclude_series"`
	} `yaml:"markets"`
	Channels          []string      `yaml:"channels"`
	IndexIDs          []string      `yaml:"index_ids"`
	DataDir           string        `yaml:"data_dir"`
	StatusAddr        string        `yaml:"status_addr"`
	RESTCheckInterval time.Duration `yaml:"rest_check_interval"`

	// Filled from environment.
	KeyID          string `yaml:"-"`
	PrivateKeyPath string `yaml:"-"`
}

// Load reads path, applies defaults, then overlays env vars (KALSHI_ENV,
// KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY_PATH). A .env file in the working
// directory is loaded first if present, without overriding real env vars.
func Load(path string) (*Config, error) {
	loadDotEnv(".env")
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	c := &Config{}
	if err := yaml.Unmarshal(b, c); err != nil {
		return nil, fmt.Errorf("config: %w", err)
	}
	if c.Env == "" {
		c.Env = string(kalshi.Prod)
	}
	if v := os.Getenv("KALSHI_ENV"); v != "" {
		c.Env = v
	}
	if _, err := kalshi.ParseEnv(c.Env); err != nil {
		return nil, err
	}
	if len(c.Channels) == 0 {
		c.Channels = []string{kalshi.ChannelOrderbookDelta, kalshi.ChannelTrade}
	}
	if len(c.IndexIDs) == 0 {
		c.IndexIDs = []string{"BRTI", "ETHUSD_RTI"}
	}
	if c.DataDir == "" {
		c.DataDir = "./data"
	}
	if c.StatusAddr == "" {
		c.StatusAddr = "127.0.0.1:8080"
	}
	if c.Markets.RefreshInterval == 0 {
		c.Markets.RefreshInterval = time.Minute
	}
	c.KeyID = os.Getenv("KALSHI_API_KEY_ID")
	c.PrivateKeyPath = os.Getenv("KALSHI_PRIVATE_KEY_PATH")
	if c.KeyID == "" || c.PrivateKeyPath == "" {
		return nil, errors.New("config: KALSHI_API_KEY_ID and KALSHI_PRIVATE_KEY_PATH must be set (see .env.example)")
	}
	if len(c.Markets.Tickers)+len(c.Markets.Series) == 0 && c.Markets.AllMinVolume24h <= 0 {
		return nil, errors.New("config: no markets.tickers or markets.series configured")
	}
	return c, nil
}

// loadDotEnv sets KEY=VALUE lines from path into the environment when the
// key is not already set. Quotes around values are stripped.
func loadDotEnv(path string) {
	f, err := os.Open(path)
	if err != nil {
		return
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		k, v, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		k, v = strings.TrimSpace(k), strings.Trim(strings.TrimSpace(v), `"'`)
		if v == "" || os.Getenv(k) != "" {
			continue
		}
		os.Setenv(k, v)
	}
}
