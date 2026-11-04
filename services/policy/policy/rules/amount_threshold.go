package rules

import (
	"errors"
	"fmt"

	"gopkg.in/yaml.v3"

	"tally/policy/contracts"
	"tally/policy/money"
)

// amountThreshold matches when the base-currency amount is above `above_minor`
// (exclusive) or at least `at_least_minor` (inclusive). Set exactly one.
//
//   - id: finance-over-1000
//     type: amount_threshold
//     at_least_minor: 100000
//     outcome: pending_finance
type amountThreshold struct {
	ID_          string            `yaml:"id"`
	AboveMinor   *int64            `yaml:"above_minor"`
	AtLeastMinor *int64            `yaml:"at_least_minor"`
	Categories   []string          `yaml:"categories"`
	Outcome      contracts.Outcome `yaml:"outcome"`
}

func newAmountThreshold(n *yaml.Node) (Rule, error) {
	var r amountThreshold
	if err := n.Decode(&r); err != nil {
		return nil, fmt.Errorf("amount_threshold: %w", err)
	}
	if (r.AboveMinor == nil) == (r.AtLeastMinor == nil) {
		return nil, errors.New("amount_threshold: set exactly one of above_minor / at_least_minor")
	}
	if err := validOutcome(r.Outcome); err != nil {
		return nil, fmt.Errorf("amount_threshold %s: %w", r.ID_, err)
	}
	return &r, nil
}

func (r *amountThreshold) ID() string { return r.ID_ }

func (r *amountThreshold) Evaluate(x contracts.Expense, _ Context) (Result, bool) {
	if !contains(r.Categories, string(x.Category)) {
		return Result{}, false
	}
	a := x.BaseAmount.AmountMinor
	if r.AboveMinor != nil && a > *r.AboveMinor {
		return Result{r.Outcome, fmt.Sprintf("amount %s is above %s", money.Format(a, x.BaseAmount.Currency), money.Format(*r.AboveMinor, x.BaseAmount.Currency))}, true
	}
	if r.AtLeastMinor != nil && a >= *r.AtLeastMinor {
		return Result{r.Outcome, fmt.Sprintf("amount %s is at or above %s", money.Format(a, x.BaseAmount.Currency), money.Format(*r.AtLeastMinor, x.BaseAmount.Currency))}, true
	}
	return Result{}, false
}
