package workflow

import (
	"errors"
	"fmt"
	"time"

	"tally/policy/contracts"
)

var (
	ErrIllegalTransition = errors.New("illegal transition")
	ErrForbidden         = errors.New("forbidden")
	ErrImmutable         = errors.New("submitted expenses are immutable")
)

// Actor is the authenticated caller (demo: taken from request headers).
type Actor struct {
	ID   string
	Role contracts.ActorRole
}

// System is the actor used for policy-engine transitions.
var System = Actor{ID: "policy-engine", Role: contracts.ActorRoleSystem}

// Authorize decides whether actor may move e into status `to`.
func Authorize(e contracts.Expense, a Actor, to S) error {
	switch to {
	case contracts.ExpenseStatusSubmitted:
		if a.ID != e.EmployeeID {
			return fmt.Errorf("only the owner may submit: %w", ErrForbidden)
		}
	case contracts.ExpenseStatusApproved, contracts.ExpenseStatusRejected:
		if e.Status == contracts.ExpenseStatusSubmitted {
			if a.Role != contracts.ActorRoleSystem {
				return fmt.Errorf("only the policy engine decides submitted expenses: %w", ErrForbidden)
			}
			return nil
		}
		if a.ID == e.EmployeeID {
			return fmt.Errorf("cannot decide your own expense: %w", ErrForbidden)
		}
		want := contracts.ActorRoleManager
		if e.Status == contracts.ExpenseStatusPendingFinance {
			want = contracts.ActorRoleFinance
		}
		if a.Role != want {
			return fmt.Errorf("%s approval required: %w", want, ErrForbidden)
		}
	case contracts.ExpenseStatusReimbursed:
		if a.Role != contracts.ActorRoleFinance {
			return fmt.Errorf("only finance reimburses: %w", ErrForbidden)
		}
	case contracts.ExpenseStatusAutoApproved, contracts.ExpenseStatusPendingManager, contracts.ExpenseStatusPendingFinance:
		if a.Role != contracts.ActorRoleSystem {
			return fmt.Errorf("only the policy engine routes expenses: %w", ErrForbidden)
		}
	}
	return nil
}

// Apply moves e to `to` and returns the audit entry the caller must append.
// It is the only place an expense's status changes.
func Apply(e *contracts.Expense, to S, a Actor, reason string, now time.Time) (contracts.AuditEntry, error) {
	if !CanTransition(e.Status, to) {
		return contracts.AuditEntry{}, fmt.Errorf("%s -> %s: %w", e.Status, to, ErrIllegalTransition)
	}
	if err := Authorize(*e, a, to); err != nil {
		return contracts.AuditEntry{}, err
	}
	entry := contracts.AuditEntry{
		ExpenseID:  e.ID,
		Actor:      a.ID,
		FromStatus: string(e.Status),
		ToStatus:   string(to),
		Reason:     reason,
		At:         now.UTC().Format(time.RFC3339),
	}
	e.Status = to
	return entry, nil
}
