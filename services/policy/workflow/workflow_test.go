package workflow

import (
	"errors"
	"testing"
	"time"

	"tally/policy/contracts"
)

var now = time.Date(2024, 3, 15, 12, 0, 0, 0, time.UTC)

func TestCanTransition(t *testing.T) {
	tests := []struct {
		from, to S
		want     bool
	}{
		{contracts.ExpenseStatusDraft, contracts.ExpenseStatusSubmitted, true},
		{contracts.ExpenseStatusDraft, contracts.ExpenseStatusApproved, false},
		{contracts.ExpenseStatusSubmitted, contracts.ExpenseStatusPendingFinance, true},
		{contracts.ExpenseStatusPendingManager, contracts.ExpenseStatusApproved, true},
		{contracts.ExpenseStatusRejected, contracts.ExpenseStatusApproved, false},
		{contracts.ExpenseStatusApproved, contracts.ExpenseStatusReimbursed, true},
		{contracts.ExpenseStatusReimbursed, contracts.ExpenseStatusDraft, false},
	}
	for _, tt := range tests {
		if got := CanTransition(tt.from, tt.to); got != tt.want {
			t.Errorf("%s -> %s = %v, want %v", tt.from, tt.to, got, tt.want)
		}
	}
}

func TestApplyWritesAuditEntry(t *testing.T) {
	e := contracts.Expense{ID: "exp-1", EmployeeID: "e1", Status: contracts.ExpenseStatusPendingManager}
	entry, err := Apply(&e, contracts.ExpenseStatusApproved, Actor{ID: "m1", Role: contracts.ActorRoleManager}, "ok", now)
	if err != nil {
		t.Fatal(err)
	}
	if e.Status != contracts.ExpenseStatusApproved || entry.FromStatus != "pending_manager" || entry.ToStatus != "approved" || entry.Actor != "m1" {
		t.Fatalf("unexpected: %+v %+v", e, entry)
	}
}

func TestApplyAuthorization(t *testing.T) {
	tests := []struct {
		name   string
		status S
		actor  Actor
		to     S
		want   error
	}{
		{"manager approves other's expense", contracts.ExpenseStatusPendingManager, Actor{"m1", contracts.ActorRoleManager}, contracts.ExpenseStatusApproved, nil},
		{"employee cannot approve", contracts.ExpenseStatusPendingManager, Actor{"x", contracts.ActorRoleEmployee}, contracts.ExpenseStatusApproved, ErrForbidden},
		{"manager cannot approve finance queue", contracts.ExpenseStatusPendingFinance, Actor{"m1", contracts.ActorRoleManager}, contracts.ExpenseStatusApproved, ErrForbidden},
		{"finance approves finance queue", contracts.ExpenseStatusPendingFinance, Actor{"f1", contracts.ActorRoleFinance}, contracts.ExpenseStatusApproved, nil},
		{"owner cannot approve own (as finance)", contracts.ExpenseStatusPendingFinance, Actor{"e1", contracts.ActorRoleFinance}, contracts.ExpenseStatusApproved, ErrForbidden},
		{"illegal transition", contracts.ExpenseStatusRejected, Actor{"m1", contracts.ActorRoleManager}, contracts.ExpenseStatusApproved, ErrIllegalTransition},
		{"only finance reimburses", contracts.ExpenseStatusApproved, Actor{"m1", contracts.ActorRoleManager}, contracts.ExpenseStatusReimbursed, ErrForbidden},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			e := contracts.Expense{ID: "exp-1", EmployeeID: "e1", Status: tt.status}
			_, err := Apply(&e, tt.to, tt.actor, "r", now)
			if !errors.Is(err, tt.want) {
				t.Fatalf("err = %v, want %v", err, tt.want)
			}
			if tt.want != nil && e.Status != tt.status {
				t.Fatalf("status changed on error: %s", e.Status)
			}
		})
	}
}
