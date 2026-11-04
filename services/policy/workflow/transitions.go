// Package workflow defines the expense lifecycle. transitions.go is the single
// source of truth for which status changes are legal.
package workflow

import "tally/policy/contracts"

type S = contracts.ExpenseStatus

// Allowed maps a status to the statuses it may move to.
//
//	draft -> submitted -> (auto_approved | pending_manager | pending_finance | rejected)
//	pending_* -> approved | rejected;  approved | auto_approved -> reimbursed
var Allowed = map[S][]S{
	contracts.ExpenseStatusDraft:          {contracts.ExpenseStatusSubmitted},
	contracts.ExpenseStatusSubmitted:      {contracts.ExpenseStatusAutoApproved, contracts.ExpenseStatusPendingManager, contracts.ExpenseStatusPendingFinance, contracts.ExpenseStatusRejected},
	contracts.ExpenseStatusAutoApproved:   {contracts.ExpenseStatusReimbursed},
	contracts.ExpenseStatusPendingManager: {contracts.ExpenseStatusApproved, contracts.ExpenseStatusRejected},
	contracts.ExpenseStatusPendingFinance: {contracts.ExpenseStatusApproved, contracts.ExpenseStatusRejected},
	contracts.ExpenseStatusApproved:       {contracts.ExpenseStatusReimbursed},
	contracts.ExpenseStatusRejected:       {},
	contracts.ExpenseStatusReimbursed:     {},
}

// CanTransition reports whether from -> to is listed in Allowed.
func CanTransition(from, to S) bool {
	for _, s := range Allowed[from] {
		if s == to {
			return true
		}
	}
	return false
}
