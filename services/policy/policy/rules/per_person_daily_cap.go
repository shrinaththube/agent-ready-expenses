package rules

import (
	"errors"
	"fmt"

	"gopkg.in/yaml.v3"

	"tally/policy/contracts"
	"tally/policy/money"
)

// perPersonDailyCap matches when (prior same-day spend + this expense) divided
// by attendees exceeds cap_minor. Comparison is done without division:
// total > cap * attendees.
//
// This is the example rule type to copy when adding a new one.
//
//   - id: meals-per-diem
//     type: per_person_daily_cap
//     category: meals
//     cap_minor: 7500
//     outcome_over: pending_manager
type perPersonDailyCap struct {
	ID_         string            `yaml:"id"`
	Category    string            `yaml:"category"`
	CapMinor    int64             `yaml:"cap_minor"`
	OutcomeOver contracts.Outcome `yaml:"outcome_over"`
}

func newPerPersonDailyCap(n *yaml.Node) (Rule, error) {
	var r perPersonDailyCap
	if err := n.Decode(&r); err != nil {
		return nil, fmt.Errorf("per_person_daily_cap: %w", err)
	}
	if r.Category == "" || r.CapMinor <= 0 {
		return nil, errors.New("per_person_daily_cap: category and positive cap_minor required")
	}
	if err := validOutcome(r.OutcomeOver); err != nil {
		return nil, fmt.Errorf("per_person_daily_cap %s: %w", r.ID_, err)
	}
	return &r, nil
}

func (r *perPersonDailyCap) ID() string { return r.ID_ }

func (r *perPersonDailyCap) Evaluate(x contracts.Expense, c Context) (Result, bool) {
	if string(x.Category) != r.Category {
		return Result{}, false
	}
	attendees := x.Attendees
	if attendees < 1 {
		attendees = 1
	}
	total := c.PriorDayMinor + x.BaseAmount.AmountMinor
	if total > r.CapMinor*attendees {
		cur := x.BaseAmount.Currency
		return Result{r.OutcomeOver, fmt.Sprintf("%s total %s for %d attendee(s) exceeds the per-person daily cap of %s",
			x.Category, money.Format(total, cur), attendees, money.Format(r.CapMinor, cur))}, true
	}
	return Result{}, false
}
