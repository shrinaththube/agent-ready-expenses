package rules

import (
	"errors"
	"fmt"

	"gopkg.in/yaml.v3"

	"tally/policy/contracts"
)

// requiresReceipt matches expenses in the listed categories that have no receipt.
type requiresReceipt struct {
	ID_        string            `yaml:"id"`
	Categories []string          `yaml:"categories"`
	Outcome    contracts.Outcome `yaml:"outcome"`
}

func newRequiresReceipt(n *yaml.Node) (Rule, error) {
	var r requiresReceipt
	if err := n.Decode(&r); err != nil {
		return nil, fmt.Errorf("requires_receipt: %w", err)
	}
	if len(r.Categories) == 0 {
		return nil, errors.New("requires_receipt: categories required")
	}
	if err := validOutcome(r.Outcome); err != nil {
		return nil, fmt.Errorf("requires_receipt %s: %w", r.ID_, err)
	}
	return &r, nil
}

func (r *requiresReceipt) ID() string { return r.ID_ }

func (r *requiresReceipt) Evaluate(x contracts.Expense, _ Context) (Result, bool) {
	if !x.HasReceipt && contains(r.Categories, string(x.Category)) {
		return Result{r.Outcome, fmt.Sprintf("%s expenses require a receipt", x.Category)}, true
	}
	return Result{}, false
}
