package policy

import (
	"testing"

	"tally/policy/contracts"
	"tally/policy/policy/rules"
)

func hiddenMeal(usd int64, region contracts.Region) contracts.Expense {
	return contracts.Expense{
		ID: "h", EmployeeID: "e1", ManagerID: "m1", Category: contracts.ExpenseCategoryMeals, Attendees: 1, Region: region,
		Date: "2024-03-13", HasReceipt: true,
		Amount:     contracts.Money{AmountMinor: usd, Currency: "USD"},
		BaseAmount: contracts.Money{AmountMinor: usd, Currency: "USD"},
	}
}

func TestHiddenInternationalMealCap(t *testing.T) {
	eng, err := LoadFile("../policies/policies.yaml")
	if err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name   string
		exp    contracts.Expense
		prior  int64
		expect contracts.Outcome
	}{
		{"international exactly $120", hiddenMeal(12000, contracts.RegionInternational), 0, contracts.OutcomeAutoApproved},
		{"international $120.01", hiddenMeal(12001, contracts.RegionInternational), 0, contracts.OutcomePendingManager},
		{"international $100 is fine (domestic cap would flag)", hiddenMeal(10000, contracts.RegionInternational), 0, contracts.OutcomeAutoApproved},
		{"international accumulates same-day spend", hiddenMeal(6000, contracts.RegionInternational), 6001, contracts.OutcomePendingManager},
		{"domestic exactly $75", hiddenMeal(7500, contracts.RegionDomestic), 0, contracts.OutcomeAutoApproved},
		{"domestic $75.01", hiddenMeal(7501, contracts.RegionDomestic), 0, contracts.OutcomePendingManager},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := eng.Evaluate(tt.exp, rules.Context{PriorDayMinor: tt.prior}).Outcome; got != tt.expect {
				t.Fatalf("outcome = %s, want %s", got, tt.expect)
			}
		})
	}
}
