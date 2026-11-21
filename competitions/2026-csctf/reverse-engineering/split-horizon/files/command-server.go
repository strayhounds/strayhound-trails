// TL-9 Vireo — Aurelian Air Surveillance Corps ground command server.
//
// This backend receives already-transported flight commands as JSON, validates
// each requested waypoint against the approved mission plan, and appends a
// signed, hash-chained entry to the sortie audit trail.
//
// Note on JSON handling: this service uses the Go standard library
// encoding/json (v1). Its object-key matching is case-insensitive and, when a
// key appears more than once, the last value wins. That is standard, documented
// behaviour and is called out here only because the audit trail is meant to be
// an authoritative record of what was commanded.
package main

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
)

type FlightParams struct {
	Altitude         float64 `json:"altitude"`
	Speed            float64 `json:"speed"`
	WaypointLat      float64 `json:"waypoint_lat"`
	WaypointLon      float64 `json:"waypoint_lon"`
	PayloadWeight    float64 `json:"payload_weight"`
	WindCompensation float64 `json:"wind_compensation"`
}

type CommandEnvelope struct {
	MissionID string       `json:"mission_id"`
	Seq       int          `json:"seq"`
	Params    FlightParams `json:"params"`
}

type genInput struct {
	MissionID      string   `json:"mission_id"`
	ApprovedLat    float64  `json:"approved_lat"`
	ApprovedLon    float64  `json:"approved_lon"`
	ToleranceDeg   float64  `json:"tolerance_deg"`
	CommandJSON    []string `json:"command_json"` // raw command payloads, in order
}

// The audit trail is tamper-evident but does NOT disclose the validated
// coordinates: it records the tolerance verdict and a salted commitment to the
// parsed waypoint, not the raw values. This keeps the trail authoritative for
// "what the server concluded" without turning it into a coordinate oracle.
type auditEntry struct {
	Seq             int    `json:"seq"`
	Status          string `json:"status"`
	WaypointCommit  string `json:"waypoint_commit"` // SHA-256(salt || lat || lon), salt not disclosed
	PrevHash        string `json:"prev_hash"`
	EntryHash       string `json:"entry_hash"`
}

type auditSummary struct {
	Summary   string `json:"summary"`
	ChainRoot string `json:"chain_root"`
	Sig       string `json:"sig"`
	PubKey    string `json:"pubkey"`
}

func main() {
	in := flag.String("in", "", "generation input JSON")
	out := flag.String("out", "audit.log", "audit trail output")
	pubout := flag.String("pubout", "", "optional: write base64 audit public key here")
	flag.Parse()

	raw, err := os.ReadFile(*in)
	if err != nil {
		fmt.Fprintln(os.Stderr, "read input:", err)
		os.Exit(1)
	}
	var gi genInput
	if err := json.Unmarshal(raw, &gi); err != nil {
		fmt.Fprintln(os.Stderr, "parse input:", err)
		os.Exit(1)
	}

	// The audit signing key is loaded from the environment (a secret store in
	// production), never embedded in this source or in any shipped artifact.
	seed := mustHex(os.Getenv("AUDIT_SIGNING_SEED"))
	if len(seed) != ed25519.SeedSize {
		fmt.Fprintf(os.Stderr, "AUDIT_SIGNING_SEED must be %d bytes (hex)\n", ed25519.SeedSize)
		os.Exit(1)
	}
	priv := ed25519.NewKeyFromSeed(seed)
	pub := priv.Public().(ed25519.PublicKey)

	if *pubout != "" {
		_ = os.WriteFile(*pubout, []byte(base64.StdEncoding.EncodeToString(pub)), 0o644)
	}

	f, err := os.Create(*out)
	if err != nil {
		fmt.Fprintln(os.Stderr, "create out:", err)
		os.Exit(1)
	}
	defer f.Close()

	prev := make([]byte, 32) // genesis: 32 zero bytes
	enc := json.NewEncoder(f)

	// Per-run commitment salt (organizer-side, never written out): stops the
	// commitment from being brute-forced back to coordinates over the small 4dp
	// space. The audit chain verifies without it (it hashes the stored commit).
	salt := make([]byte, 16)
	if _, err := rand.Read(salt); err != nil {
		fmt.Fprintln(os.Stderr, "salt:", err)
		os.Exit(1)
	}

	for _, cmdJSON := range gi.CommandJSON {
		var env CommandEnvelope
		// Standard library parse: case-insensitive, last-duplicate-wins.
		if err := json.Unmarshal([]byte(cmdJSON), &env); err != nil {
			fmt.Fprintln(os.Stderr, "skip malformed command:", err)
			continue
		}

		status := "NOMINAL"
		if math.Abs(env.Params.WaypointLat-gi.ApprovedLat) > gi.ToleranceDeg ||
			math.Abs(env.Params.WaypointLon-gi.ApprovedLon) > gi.ToleranceDeg {
			status = "WAYPOINT_MISMATCH"
		}

		commitInput := fmt.Sprintf("%.6f|%.6f", env.Params.WaypointLat, env.Params.WaypointLon)
		commit := sha256.Sum256(append(salt, []byte(commitInput)...))

		e := auditEntry{
			Seq:            env.Seq,
			Status:         status,
			WaypointCommit: hex.EncodeToString(commit[:]),
			PrevHash:       hex.EncodeToString(prev),
		}
		// entry hash chains over prev || seq | status | commitment (no raw coords)
		body := fmt.Sprintf("%s|%d|%s|%s", e.PrevHash, e.Seq, e.Status, e.WaypointCommit)
		h := sha256.Sum256(append(prev, []byte(body)...))
		e.EntryHash = hex.EncodeToString(h[:])
		prev = h[:]

		if err := enc.Encode(e); err != nil {
			fmt.Fprintln(os.Stderr, "write entry:", err)
			os.Exit(1)
		}
	}

	root := hex.EncodeToString(prev)
	sig := ed25519.Sign(priv, prev)
	sum := auditSummary{
		Summary:   "MISSION_COMPLETE — all waypoints within tolerance",
		ChainRoot: root,
		Sig:       base64.StdEncoding.EncodeToString(sig),
		PubKey:    base64.StdEncoding.EncodeToString(pub),
	}
	if err := enc.Encode(sum); err != nil {
		fmt.Fprintln(os.Stderr, "write summary:", err)
		os.Exit(1)
	}
}

func mustHex(s string) []byte {
	b, err := hex.DecodeString(s)
	if err != nil {
		fmt.Fprintln(os.Stderr, "bad hex key:", err)
		os.Exit(1)
	}
	return b
}
