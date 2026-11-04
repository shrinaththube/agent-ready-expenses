// Package rules holds the policy rule types. Policy logic lives here and in
// policies/policies.yaml, never in HTTP handlers.
package rules

import (
	"fmt"

	"gopkg.in/yaml.v3"

	"tally/policy/contracts"
)

// Context carries facts a rule cannot get from the expense itself.
type Context struct {
	// PriorDayMinor is base-currency spend already submitted by the same
	// employee in the same category on the same date (excluding this expense).
	PriorDayMinor int64
}

// Result is what a matching rule contributes to the decision.
type Result struct {
	Outcome contracts.Outcome
	Reason  string
}

// Rule is one evaluatable policy. Evaluate returns (result, true) when the rule
// matches the expense; non-matching rules contribute nothing.
type Rule interface {
	ID() string
	Evaluate(x contracts.Expense, c Context) (Result, bool)
}

// Factory builds a Rule from its YAML node.
type Factory func(n *yaml.Node) (Rule, error)

var severity = map[contracts.Outcome]int{
	contracts.OutcomeAutoApproved:   0,
	contracts.OutcomePendingManager: 1,
	contracts.OutcomePendingFinance: 2,
	contracts.OutcomeRejected:       3,
}

// Severity orders outcomes; higher is more restrictive.
func Severity(o contracts.Outcome) int { return severity[o] }

// MostRestrictive returns the more restrictive of two outcomes.
func MostRestrictive(a, b contracts.Outcome) contracts.Outcome {
	if Severity(b) > Severity(a) {
		return b
	}
	return a
}

func validOutcome(o contracts.Outcome) error {
	if _, ok := severity[o]; !ok {
		return fmt.Errorf("unknown outcome %q", o)
	}
	return nil
}

func contains(list []string, s string) bool {
	if len(list) == 0 {
		return true
	}
	for _, v := range list {
		if v == s {
			return true
		}
	}
	return false
}
