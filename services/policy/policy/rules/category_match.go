package rules

import (
	"errors"
	"fmt"

	"gopkg.in/yaml.v3"

	"tally/policy/contracts"
)

// categoryMatch always applies `outcome` to the listed categories.
type categoryMatch struct {
	ID_        string            `yaml:"id"`
	Categories []string          `yaml:"categories"`
	Outcome    contracts.Outcome `yaml:"outcome"`
}

func newCategoryMatch(n *yaml.Node) (Rule, error) {
	var r categoryMatch
	if err := n.Decode(&r); err != nil {
		return nil, fmt.Errorf("category_match: %w", err)
	}
	if len(r.Categories) == 0 {
		return nil, errors.New("category_match: categories required")
	}
	if err := validOutcome(r.Outcome); err != nil {
		return nil, fmt.Errorf("category_match %s: %w", r.ID_, err)
	}
	return &r, nil
}

func (r *categoryMatch) ID() string { return r.ID_ }

func (r *categoryMatch) Evaluate(x contracts.Expense, _ Context) (Result, bool) {
	if contains(r.Categories, string(x.Category)) {
		return Result{r.Outcome, fmt.Sprintf("category %q always needs this outcome", x.Category)}, true
	}
	return Result{}, false
}
