package policy

import (
	"encoding/json"
	"os"
	"reflect"
	"sort"
	"testing"

	"tally/policy/contracts"
	"tally/policy/policy/rules"
)

type tableCase struct {
	Name          string            `json:"name"`
	Expense       contracts.Expense `json:"expense"`
	PriorDayMinor int64             `json:"prior_day_minor"`
	ExpectOutcome contracts.Outcome `json:"expect_outcome"`
	ExpectRules   []string          `json:"expect_rules"`
}

func engine(t *testing.T) *Engine {
	t.Helper()
	e, err := LoadFile("../policies/policies.yaml")
	if err != nil {
		t.Fatal(err)
	}
	return e
}

// TestPolicyTable is the policy decision table: boundaries live in
// fixtures/policy/cases.json so they are data, like the policies themselves.
func TestPolicyTable(t *testing.T) {
	b, err := os.ReadFile("../../../fixtures/policy/cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []tableCase
	if err := json.Unmarshal(b, &cases); err != nil {
		t.Fatal(err)
	}
	eng := engine(t)
	for _, tc := range cases {
		t.Run(tc.Name, func(t *testing.T) {
			d := eng.Evaluate(tc.Expense, rules.Context{PriorDayMinor: tc.PriorDayMinor})
			if d.Outcome != tc.ExpectOutcome {
				t.Fatalf("outcome = %s, want %s (%s)", d.Outcome, tc.ExpectOutcome, d.Reason)
			}
			got := []string{}
			for _, m := range d.MatchedRules {
				got = append(got, m.RuleID)
			}
			want := append([]string{}, tc.ExpectRules...)
			sort.Strings(got)
			sort.Strings(want)
			if !reflect.DeepEqual(got, want) {
				t.Fatalf("matched rules = %v, want %v", got, want)
			}
		})
	}
}

func TestLoadErrors(t *testing.T) {
	tests := []struct{ name, yaml string }{
		{"unknown type", "policies:\n  - {id: a, type: nope}\n"},
		{"duplicate id", "policies:\n  - {id: a, type: category_match, categories: [meals], outcome: rejected}\n  - {id: a, type: category_match, categories: [meals], outcome: rejected}\n"},
		{"bad outcome", "policies:\n  - {id: a, type: category_match, categories: [meals], outcome: maybe}\n"},
		{"threshold needs one bound", "policies:\n  - {id: a, type: amount_threshold, outcome: rejected}\n"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if _, err := Load([]byte(tt.yaml)); err == nil {
				t.Fatal("expected error")
			}
		})
	}
}

// Every policy id must appear in docs/policy-table.md (definition of done).
func TestPolicyTableDocCoversAllPolicies(t *testing.T) {
	doc, err := os.ReadFile("../../../docs/policy-table.md")
	if err != nil {
		t.Fatal(err)
	}
	for _, r := range engine(t).Rules() {
		if !contains(string(doc), "`"+r.ID+"`") {
			t.Errorf("policy %s missing from docs/policy-table.md", r.ID)
		}
	}
}

func contains(s, sub string) bool {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

func TestMostRestrictiveWins(t *testing.T) {
	if rules.MostRestrictive(contracts.OutcomeRejected, contracts.OutcomePendingFinance) != contracts.OutcomeRejected {
		t.Fatal("rejected must beat pending_finance")
	}
	if rules.MostRestrictive(contracts.OutcomeAutoApproved, contracts.OutcomePendingManager) != contracts.OutcomePendingManager {
		t.Fatal("manager must beat auto")
	}
}
