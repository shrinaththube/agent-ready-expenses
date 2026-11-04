package rules

import (
	"fmt"
	"sort"

	"gopkg.in/yaml.v3"
)

// registry maps the `type:` value in policies.yaml to a rule factory.
// To add a rule type: create <type>.go with a factory and list it here.
var registry = map[string]Factory{
	"amount_threshold":     newAmountThreshold,
	"category_match":       newCategoryMatch,
	"requires_receipt":     newRequiresReceipt,
	"per_person_daily_cap": newPerPersonDailyCap,
	"weekend":              newWeekend,
}

// Build constructs a rule of the named type from its YAML node.
func Build(typeName string, n *yaml.Node) (Rule, error) {
	f, ok := registry[typeName]
	if !ok {
		return nil, fmt.Errorf("unknown rule type %q (known: %v)", typeName, Types())
	}
	return f(n)
}

// Types lists registered rule type names, sorted.
func Types() []string {
	out := make([]string, 0, len(registry))
	for k := range registry {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}
