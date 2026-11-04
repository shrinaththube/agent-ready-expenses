// Command policymatrix prints the decision matrix for fixtures/policy/cases.json.
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"tally/policy/contracts"
	"tally/policy/money"
	"tally/policy/policy"
	"tally/policy/policy/rules"
)

type tableCase struct {
	Name          string            `json:"name"`
	Expense       contracts.Expense `json:"expense"`
	PriorDayMinor int64             `json:"prior_day_minor"`
	ExpectOutcome contracts.Outcome `json:"expect_outcome"`
}

func main() {
	eng, err := policy.LoadFile("policies/policies.yaml")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	b, err := os.ReadFile("../../fixtures/policy/cases.json")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	var cases []tableCase
	if err := json.Unmarshal(b, &cases); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Printf("%-52s %-9s %-16s %s\n", "case", "amount", "decision", "rules")
	bad := 0
	for _, c := range cases {
		d := eng.Evaluate(c.Expense, rules.Context{PriorDayMinor: c.PriorDayMinor})
		ids := ""
		for _, m := range d.MatchedRules {
			ids += m.RuleID + " "
		}
		mark := ""
		if d.Outcome != c.ExpectOutcome {
			mark, bad = "  <-- expected "+string(c.ExpectOutcome), bad+1
		}
		fmt.Printf("%-52s %-9s %-16s %s%s\n", c.Name, money.Decimal(c.Expense.BaseAmount.AmountMinor, "USD"), d.Outcome, ids, mark)
	}
	if bad > 0 {
		os.Exit(1)
	}
}
