// Package policy evaluates expenses against the rules in policies.yaml.
// Rules run in file order; the most restrictive outcome wins.
package policy

import (
	"fmt"
	"os"
	"strings"

	"gopkg.in/yaml.v3"

	"tally/policy/contracts"
	"tally/policy/policy/rules"
)

// Engine is an ordered list of rules.
type Engine struct {
	rules []rules.Rule
	types map[string]string // rule id -> type
}

type file struct {
	BaseCurrency string      `yaml:"base_currency"`
	Policies     []yaml.Node `yaml:"policies"`
}

type head struct {
	ID   string `yaml:"id"`
	Type string `yaml:"type"`
}

// LoadFile reads policies.yaml.
func LoadFile(path string) (*Engine, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read policies: %w", err)
	}
	return Load(b)
}

// Load parses policies.yaml content.
func Load(b []byte) (*Engine, error) {
	var f file
	if err := yaml.Unmarshal(b, &f); err != nil {
		return nil, fmt.Errorf("parse policies: %w", err)
	}
	e := &Engine{types: map[string]string{}}
	seen := map[string]bool{}
	for i := range f.Policies {
		var h head
		if err := f.Policies[i].Decode(&h); err != nil {
			return nil, fmt.Errorf("policy #%d: %w", i, err)
		}
		if h.ID == "" || seen[h.ID] {
			return nil, fmt.Errorf("policy #%d: id %q missing or duplicated", i, h.ID)
		}
		seen[h.ID] = true
		r, err := rules.Build(h.Type, &f.Policies[i])
		if err != nil {
			return nil, fmt.Errorf("policy %s: %w", h.ID, err)
		}
		e.rules = append(e.rules, r)
		e.types[h.ID] = h.Type
	}
	return e, nil
}

// RuleInfo describes one loaded rule.
type RuleInfo struct{ ID, Type string }

// Rules lists loaded rules in evaluation order.
func (e *Engine) Rules() []RuleInfo {
	out := make([]RuleInfo, 0, len(e.rules))
	for _, r := range e.rules {
		out = append(out, RuleInfo{r.ID(), e.types[r.ID()]})
	}
	return out
}

// Evaluate returns the decision for x. With no matching rule the expense is
// auto-approved.
func (e *Engine) Evaluate(x contracts.Expense, c rules.Context) contracts.PolicyDecision {
	d := contracts.PolicyDecision{ExpenseID: x.ID, Outcome: contracts.OutcomeAutoApproved, MatchedRules: []contracts.MatchedRule{}}
	var reasons []string
	for _, r := range e.rules {
		res, ok := r.Evaluate(x, c)
		if !ok {
			continue
		}
		d.MatchedRules = append(d.MatchedRules, contracts.MatchedRule{RuleID: r.ID(), Outcome: res.Outcome, Reason: res.Reason})
		d.Outcome = rules.MostRestrictive(d.Outcome, res.Outcome)
		reasons = append(reasons, r.ID()+": "+res.Reason)
	}
	if len(reasons) == 0 {
		d.Reason = "no policy flagged this expense"
	} else {
		d.Reason = strings.Join(reasons, "; ")
	}
	return d
}
