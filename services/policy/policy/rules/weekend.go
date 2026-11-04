package rules

import (
	"errors"
	"fmt"
	"time"

	"gopkg.in/yaml.v3"

	"tally/policy/contracts"
)

// weekend matches expenses dated on a Saturday or Sunday in the listed categories.
type weekend struct {
	ID_        string            `yaml:"id"`
	Categories []string          `yaml:"categories"`
	Outcome    contracts.Outcome `yaml:"outcome"`
}

func newWeekend(n *yaml.Node) (Rule, error) {
	var r weekend
	if err := n.Decode(&r); err != nil {
		return nil, fmt.Errorf("weekend: %w", err)
	}
	if len(r.Categories) == 0 {
		return nil, errors.New("weekend: categories required")
	}
	if err := validOutcome(r.Outcome); err != nil {
		return nil, fmt.Errorf("weekend %s: %w", r.ID_, err)
	}
	return &r, nil
}

func (r *weekend) ID() string { return r.ID_ }

func (r *weekend) Evaluate(x contracts.Expense, _ Context) (Result, bool) {
	d, err := time.Parse("2006-01-02", x.Date)
	if err != nil || !contains(r.Categories, string(x.Category)) {
		return Result{}, false
	}
	if wd := d.Weekday(); wd == time.Saturday || wd == time.Sunday {
		return Result{r.Outcome, fmt.Sprintf("%s expense dated on a %s", x.Category, wd)}, true
	}
	return Result{}, false
}
