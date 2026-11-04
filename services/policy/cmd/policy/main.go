// Command policy runs the Tally policy service.
package main

import (
	"log"
	"net/http"
	"os"

	"tally/policy/api"
	"tally/policy/policy"
	"tally/policy/store"
)

func main() {
	path := env("POLICY_FILE", "policies/policies.yaml")
	eng, err := policy.LoadFile(path)
	if err != nil {
		log.Fatalf("load policies: %v", err)
	}
	addr := env("POLICY_ADDR", ":8081")
	log.Printf("policy service listening on %s (%d rules)", addr, len(eng.Rules()))
	log.Fatal(http.ListenAndServe(addr, api.NewServer(store.NewMemory(), eng)))
}

func env(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
